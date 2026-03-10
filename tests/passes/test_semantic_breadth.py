from __future__ import annotations

import pytest

from htp.passes.program_model import build_semantic_model, build_type_layout_effects, canonicalize_program


def test_build_semantic_model_tracks_channel_effects():
    canonical = canonicalize_program(
        {
            "entry": "channel_kernel",
            "target": {"backend": "generic", "option": "default"},
            "kernel": {
                "name": "channel_kernel",
                "args": [
                    {"name": "value", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                    {"name": "channel", "kind": "channel", "dtype": "i32", "shape": [], "role": "channel"},
                    {"name": "out", "kind": "scalar", "dtype": "i32", "shape": [], "role": "output"},
                ],
                "ops": [
                    {"op": "channel_send", "value": "value", "channel": "channel"},
                    {"op": "channel_recv", "channel": "channel", "out": "out"},
                ],
            },
            "workload": {
                "entry": "channel_kernel",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "channel_kernel",
                        "args": ["value", "channel", "out"],
                    }
                ],
                "channels": [{"name": "channel", "dtype": "i32", "kind": "fifo"}],
                "dependencies": [],
            },
        }
    )

    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)
    _types, _layout, effects = build_type_layout_effects(
        kernel_ir,
        workload_ir,
        target={"backend": "generic", "option": "default"},
    )

    assert kernel_ir["ops"][0]["effects"] == {
        "reads": ["value"],
        "writes": [],
        "channel_reads": [],
        "channel_writes": ["channel"],
    }
    assert kernel_ir["ops"][1]["effects"] == {
        "reads": [],
        "writes": ["out"],
        "channel_reads": ["channel"],
        "channel_writes": [],
    }
    assert effects["channels"] == [
        {
            "name": "channel",
            "dtype": "i32",
            "kind": "fifo",
            "producers": ["op0"],
            "consumers": ["op1"],
        }
    ]


def test_canonicalize_program_rejects_dependency_on_unknown_task():
    with pytest.raises(ValueError, match="HTP.WORKLOAD.UNKNOWN_TASK"):
        canonicalize_program(
            {
                "entry": "bad_workload",
                "kernel": {
                    "name": "bad_workload",
                    "args": [],
                    "ops": [],
                },
                "workload": {
                    "entry": "bad_workload",
                    "tasks": [
                        {"task_id": "task0", "kind": "kernel_call", "kernel": "bad_workload", "args": []}
                    ],
                    "channels": [],
                    "dependencies": [{"src": "task0", "dst": "task1"}],
                },
            }
        )


def test_build_type_layout_effects_rejects_nvgpu_unsupported_buffer_dtype():
    canonical = canonicalize_program(
        {
            "entry": "bad_kernel",
            "target": {"backend": "nvgpu", "option": "ampere"},
            "kernel": {
                "name": "bad_kernel",
                "args": [
                    {"name": "A", "kind": "buffer", "dtype": "f16", "shape": ["M", "K"], "role": "input"},
                    {"name": "B", "kind": "buffer", "dtype": "f16", "shape": ["K", "N"], "role": "input"},
                    {"name": "C", "kind": "buffer", "dtype": "f16", "shape": ["M", "N"], "role": "output"},
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
                        "dtype": "f16",
                    }
                ],
            },
            "workload": {
                "entry": "bad_kernel",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "bad_kernel",
                        "args": ["A", "B", "C", "M", "N", "K"],
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
        }
    )
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)

    with pytest.raises(ValueError, match="HTP.TYPECHECK.UNSUPPORTED_BUFFER_DTYPE"):
        build_type_layout_effects(kernel_ir, workload_ir, target={"backend": "nvgpu", "option": "ampere"})


def test_build_semantic_model_tracks_intrinsics_views_and_reduction_types():
    canonical = canonicalize_program(
        {
            "entry": "reduce_kernel",
            "target": {"backend": "generic", "option": "default"},
            "kernel": {
                "name": "reduce_kernel",
                "args": [
                    {"name": "src", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "input"},
                    {
                        "name": "row_view",
                        "kind": "view",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "input",
                        "alias_of": "src",
                        "source": "src",
                    },
                    {"name": "tmp", "kind": "buffer", "dtype": "f32", "shape": ["N"], "role": "temp"},
                    {"name": "out", "kind": "buffer", "dtype": "f32", "shape": ["N"], "role": "output"},
                ],
                "ops": [
                    {"op": "transpose", "source": "src", "out": "tmp", "permutation": [1, 0]},
                    {"op": "reduction_sum", "source": "tmp", "out": "out", "axis": 0},
                ],
            },
            "workload": {
                "entry": "reduce_kernel",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "reduce_kernel",
                        "args": ["src", "row_view", "tmp", "out"],
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
        }
    )

    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)
    types, _layout, effects = build_type_layout_effects(
        kernel_ir,
        workload_ir,
        target={"backend": "generic", "option": "default"},
    )

    assert [op["intrinsic"] for op in kernel_ir["ops"]] == [
        "portable.transpose",
        "portable.reduction_sum",
    ]
    assert types["buffers"]["src"]["shape"]["dims"] == [
        {"kind": "symbol", "symbol": "M"},
        {"kind": "symbol", "symbol": "N"},
    ]
    assert types["values"]["row_view"]["kind"] == "view"
    assert types["values"]["row_view"]["alias_of"] == "src"
    assert effects["writes"]["op1"] == ["out"]


def test_build_type_layout_effects_rejects_unknown_view_alias():
    canonical = canonicalize_program(
        {
            "entry": "bad_alias",
            "target": {"backend": "generic", "option": "default"},
            "kernel": {
                "name": "bad_alias",
                "args": [
                    {
                        "name": "view_only",
                        "kind": "view",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "input",
                        "alias_of": "missing_buffer",
                    }
                ],
                "ops": [],
            },
            "workload": {
                "entry": "bad_alias",
                "tasks": [
                    {"task_id": "task0", "kind": "kernel_call", "kernel": "bad_alias", "args": ["view_only"]}
                ],
                "channels": [],
                "dependencies": [],
            },
        }
    )
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)

    with pytest.raises(ValueError, match="HTP.TYPECHECK.UNKNOWN_ALIAS"):
        build_type_layout_effects(kernel_ir, workload_ir, target={"backend": "generic", "option": "default"})


def test_build_type_layout_effects_tracks_allgather_and_reduce_scatter_collectives():
    canonical = canonicalize_program(
        {
            "entry": "collective_kernel",
            "target": {"backend": "generic", "option": "default"},
            "kernel": {
                "name": "collective_kernel",
                "args": [
                    {
                        "name": "src",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["M", "N"],
                        "role": "input",
                        "distribution": [{"kind": "replicate"}, {"kind": "shard", "axis": "1"}],
                    },
                    {"name": "tmp", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "temp"},
                    {
                        "name": "out",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["M", "N"],
                        "role": "output",
                        "distribution": [{"kind": "replicate"}, {"kind": "shard", "axis": "1"}],
                    },
                ],
                "ops": [
                    {"op": "allgather", "source": "src", "out": "tmp", "axis": 1, "mesh_axis": 1},
                    {"op": "reduce_scatter", "source": "tmp", "out": "out", "axis": 1, "mesh_axis": 1},
                ],
            },
            "workload": {
                "entry": "collective_kernel",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "collective_kernel",
                        "args": ["src", "tmp", "out"],
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
        }
    )

    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)
    _types, layout, effects = build_type_layout_effects(
        kernel_ir,
        workload_ir,
        target={"backend": "generic", "option": "default"},
    )

    assert [op["intrinsic"] for op in kernel_ir["ops"]] == [
        "portable.allgather",
        "portable.reduce_scatter",
    ]
    assert [item["kind"] for item in effects["collectives"]] == ["allgather", "reduce_scatter"]
    assert effects["collectives"][0]["status"] == "discharged"
    assert effects["collectives"][1]["status"] == "discharged"
    assert layout["relayouts"][0]["kind"] == "allgather"
    assert layout["relayouts"][1]["kind"] == "reduce_scatter"


def test_build_semantic_model_emits_serving_routine_summary():
    canonical = canonicalize_program(
        {
            "entry": "serving_routine",
            "target": {"backend": "nvgpu", "option": "ampere"},
            "kernel": {
                "name": "decode_step",
                "args": [
                    {
                        "name": "hidden",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["B", "H"],
                        "role": "input",
                    },
                    {
                        "name": "weights",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["H", "H"],
                        "role": "input",
                    },
                    {
                        "name": "next_hidden",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["B", "H"],
                        "role": "output",
                    },
                ],
                "ops": [{"op": "matmul", "lhs": "hidden", "rhs": "weights", "out": "next_hidden"}],
            },
            "workload": {
                "entry": "serving_routine",
                "tasks": [
                    {
                        "task_id": "prefill",
                        "kind": "kernel_call",
                        "kernel": "decode_step",
                        "args": ["hidden", "weights", "next_hidden"],
                        "attrs": {"phase": "prefill", "state": "kv_fill", "role": "compute"},
                    },
                    {
                        "task_id": "decode",
                        "kind": "kernel_call",
                        "kernel": "decode_step",
                        "args": ["next_hidden", "weights", "next_hidden"],
                        "attrs": {"phase": "decode", "state": "token_step", "role": "compute"},
                    },
                ],
                "channels": [{"name": "tokens", "dtype": "f32", "kind": "fifo", "capacity": 2}],
                "dependencies": [{"src": "prefill", "dst": "decode"}],
            },
        }
    )

    _kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)

    assert workload_ir["routine"] == {
        "kind": "serving_routine",
        "phases": [
            {"name": "prefill", "tasks": ["prefill"], "states": ["kv_fill"]},
            {"name": "decode", "tasks": ["decode"], "states": ["token_step"]},
        ],
        "state_edges": [{"src": "kv_fill", "dst": "token_step", "via": "decode"}],
        "channel_flow": [{"channel": "tokens", "participants": [], "protocol": "fifo"}],
    }
