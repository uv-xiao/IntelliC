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
