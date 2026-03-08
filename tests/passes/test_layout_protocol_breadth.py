from __future__ import annotations

import pytest

from htp.csp import channel, process
from htp.csp import program as csp_program
from htp.passes.program_model import (
    build_schedule_plan,
    build_semantic_model,
    build_type_layout_effects,
    canonicalize_program,
)
from htp.wsp import program as wsp_program
from htp.wsp import schedule as wsp_schedule
from htp.wsp import workload as wsp_workload


def _matmul_kernel() -> dict[str, object]:
    return {
        "name": "gemm_tile",
        "args": [
            {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
            {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
            {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
            {"name": "M", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
            {"name": "N", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
            {"name": "K", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
        ],
        "ops": [
            {
                "op": "matmul",
                "lhs": "A",
                "rhs": "B",
                "out": "C",
                "m": "M",
                "n": "N",
                "k": "K",
                "dtype": "f32",
            }
        ],
    }


def test_wsp_surface_lowers_schedule_directives_into_layout_and_schedule():
    canonical = canonicalize_program(
        wsp_program(
            entry="gemm_tile",
            target={"backend": "nvgpu", "option": "ampere"},
            kernel=_matmul_kernel(),
            workload=wsp_workload(
                entry="gemm_tile",
                tasks=[
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "gemm_tile",
                        "args": ["A", "B", "C", "M", "N", "K"],
                    }
                ],
            ),
            schedule=wsp_schedule(
                tile={"block": [32, 64, 16]},
                bind={"grid": "block", "lane": "warp"},
                pipeline={"depth": 3, "buffering": "double"},
                resources={"num_warps": 4},
                specialize={"operator": "matmul"},
            ),
        )
    )

    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)
    _types, layout, effects = build_type_layout_effects(
        kernel_ir,
        workload_ir,
        target={"backend": "nvgpu", "option": "ampere"},
    )
    schedule_plan = build_schedule_plan(
        entry="gemm_tile",
        kernel_ir=kernel_ir,
        effects=effects,
        target={"backend": "nvgpu", "option": "ampere"},
        schedule_directives=canonical["schedule_directives"],
    )

    assert layout["facets"]["buffers"]["A"] == {
        "distribution": {"dims": [{"kind": "replicate"}, {"kind": "replicate"}]},
        "memory": {"space": "global", "layout": "row_major", "order": [0, 1]},
        "hardware": {"scope": "thread_block", "vector_width": 1},
    }
    assert schedule_plan["directives"] == {
        "tile": {"block": [32, 64, 16]},
        "bind": {"grid": "block", "lane": "warp"},
        "pipeline": {"depth": 3, "buffering": "double"},
        "resources": {"num_warps": 4},
        "specialize": {"operator": "matmul"},
    }
    assert schedule_plan["launch"] == {"grid": "block", "lane": "warp", "num_warps": 4}
    assert schedule_plan["buffering_strategy"] == "double"
    assert schedule_plan["legality"] == {"ok": True, "reasons": []}


def test_csp_surface_lowers_protocol_obligations_and_rejects_unbalanced_channels():
    canonical = canonicalize_program(
        csp_program(
            entry="pipeline_demo",
            kernel=_matmul_kernel(),
            channels=[channel("tiles", dtype="f32", capacity=2)],
            processes=[
                process(
                    "producer", task_id="p0", kernel="gemm_tile", puts=[{"channel": "tiles", "count": 1}]
                ),
                process(
                    "consumer", task_id="p1", kernel="gemm_tile", gets=[{"channel": "tiles", "count": 1}]
                ),
            ],
        )
    )

    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)
    _types, _layout, effects = build_type_layout_effects(
        kernel_ir,
        workload_ir,
        target={"backend": "generic", "option": "default"},
    )

    assert effects["protocols"] == [
        {
            "channel": "tiles",
            "protocol": "fifo",
            "capacity": 2,
            "puts": 1,
            "gets": 1,
            "balanced": True,
        }
    ]

    unbalanced = canonicalize_program(
        csp_program(
            entry="bad_pipeline",
            kernel=_matmul_kernel(),
            channels=[channel("tiles", dtype="f32", capacity=1)],
            processes=[
                process(
                    "producer", task_id="p0", kernel="gemm_tile", puts=[{"channel": "tiles", "count": 2}]
                ),
                process(
                    "consumer", task_id="p1", kernel="gemm_tile", gets=[{"channel": "tiles", "count": 1}]
                ),
            ],
        )
    )
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(unbalanced)

    with pytest.raises(ValueError, match="HTP.PROTOCOL.UNBALANCED_CHANNEL"):
        build_type_layout_effects(
            kernel_ir,
            workload_ir,
            target={"backend": "generic", "option": "default"},
        )
