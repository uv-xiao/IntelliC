from __future__ import annotations

import json

from htp.csp import channel, process
from htp.csp import program as csp_program
from htp.passes import analyze_schedule, typecheck_layout_effects
from htp.pipeline.defaults import run_default_pipeline
from htp.wsp import program as wsp_program
from htp.wsp import schedule as wsp_schedule
from htp.wsp import workload as wsp_workload


def _kernel() -> dict[str, object]:
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


def test_csp_protocol_invariant_is_declared_in_pass_contracts():
    assert "Effects.ProtocolBalanced@1" in typecheck_layout_effects.CONTRACT.establishes_effect_invariants
    assert "Effects.ProtocolBalanced@1" in analyze_schedule.CONTRACT.requires_effect_invariants


def test_wsp_example_pipeline_preserves_schedule_directives(tmp_path):
    package_dir = tmp_path / "wsp_pkg"
    result = run_default_pipeline(
        package_dir=package_dir,
        program=wsp_program(
            entry="gemm_tile",
            target={"backend": "nvgpu", "option": "ampere"},
            kernel=_kernel(),
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
            schedule=wsp_schedule(resources={"num_warps": 4}, pipeline={"depth": 2, "buffering": "double"}),
        ),
    )

    schedule = json.loads(
        (package_dir / "ir" / "stages" / result.current_stage / "schedule.json").read_text()
    )

    assert schedule["pipeline_depth"] >= 1
    assert result.pass_ids[-1] == "htp::emit_package@1"


def test_csp_example_pipeline_emits_protocol_effects(tmp_path):
    package_dir = tmp_path / "csp_pkg"
    result = run_default_pipeline(
        package_dir=package_dir,
        program=csp_program(
            entry="pipeline_demo",
            target={"backend": "nvgpu", "option": "ampere"},
            kernel=_kernel(),
            channels=[channel("tiles", dtype="f32", capacity=2)],
            processes=[
                process(
                    "producer", task_id="p0", kernel="gemm_tile", puts=[{"channel": "tiles", "count": 1}]
                ),
                process(
                    "consumer", task_id="p1", kernel="gemm_tile", gets=[{"channel": "tiles", "count": 1}]
                ),
            ],
        ),
    )

    effects = json.loads((package_dir / "ir" / "stages" / result.current_stage / "effects.json").read_text())

    assert effects["protocols"] == [
        {
            "channel": "tiles",
            "protocol": "fifo",
            "capacity": 2,
            "puts": 1,
            "gets": 1,
            "balanced": True,
            "participants": ["consumer", "producer"],
            "hazards": [],
            "deadlock_safe": True,
        }
    ]
