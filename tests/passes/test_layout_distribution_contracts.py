from __future__ import annotations

import pytest

from htp.passes.program_model import build_semantic_model, build_type_layout_effects, canonicalize_program


def _workload(entry: str, args: list[str]) -> dict[str, object]:
    return {
        "entry": entry,
        "tasks": [{"task_id": "task0", "kind": "kernel_call", "kernel": entry, "args": args}],
        "channels": [],
        "dependencies": [],
    }


def test_distribution_join_is_recorded_and_requires_explicit_relayout():
    canonical = canonicalize_program(
        {
            "entry": "join_kernel",
            "target": {"backend": "generic", "option": "default"},
            "kernel": {
                "name": "join_kernel",
                "args": [
                    {
                        "name": "lhs",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "input",
                        "distribution": [{"kind": "replicate"}],
                    },
                    {
                        "name": "rhs",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "input",
                        "distribution": [{"kind": "shard", "axis": "x"}],
                    },
                    {
                        "name": "out",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "output",
                        "distribution": [{"kind": "replicate"}],
                    },
                ],
                "ops": [
                    {
                        "op": "elementwise_binary",
                        "operator": "add",
                        "lhs": "lhs",
                        "rhs": "rhs",
                        "out": "out",
                    }
                ],
            },
            "workload": _workload("join_kernel", ["lhs", "rhs", "out"]),
        }
    )
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)

    with pytest.raises(ValueError, match="HTP.LAYOUT.RELAYOUT_REQUIRED"):
        build_type_layout_effects(kernel_ir, workload_ir, target={"backend": "generic", "option": "default"})

    canonical["kernel"]["args"][2]["distribution"] = [{"kind": "shard", "axis": "x"}]
    canonical["kernel"]["args"][2]["role"] = "temp"
    canonical["kernel"]["args"].append(
        {
            "name": "out_relayout",
            "kind": "buffer",
            "dtype": "f32",
            "shape": ["N"],
            "role": "output",
            "distribution": [{"kind": "replicate"}],
        }
    )
    canonical["kernel"]["ops"] = [
        {
            "op": "elementwise_binary",
            "operator": "add",
            "lhs": "lhs",
            "rhs": "rhs",
            "out": "out",
        },
        {"op": "relayout", "source": "out", "out": "out_relayout"},
    ]
    canonical["workload"] = _workload("join_kernel", ["lhs", "rhs", "out", "out_relayout"])
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)
    _types, layout, _effects = build_type_layout_effects(
        kernel_ir,
        workload_ir,
        target={"backend": "generic", "option": "default"},
    )

    assert layout["joins"] == [
        {
            "op_id": "op0",
            "lhs": "lhs",
            "rhs": "rhs",
            "out": "out",
            "ok": True,
            "joined": {"dims": [{"kind": "shard", "axis": "x"}]},
        }
    ]
    assert layout["relayouts"] == [
        {
            "op_id": "op1",
            "source": "out",
            "out": "out_relayout",
            "source_distribution": {"dims": [{"kind": "shard", "axis": "x"}]},
            "out_distribution": {"dims": [{"kind": "replicate"}]},
        }
    ]


def test_distribution_join_rejects_incompatible_shards():
    canonical = canonicalize_program(
        {
            "entry": "bad_join",
            "target": {"backend": "generic", "option": "default"},
            "kernel": {
                "name": "bad_join",
                "args": [
                    {
                        "name": "lhs",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "input",
                        "distribution": [{"kind": "shard", "axis": "x"}],
                    },
                    {
                        "name": "rhs",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "input",
                        "distribution": [{"kind": "shard", "axis": "y"}],
                    },
                    {
                        "name": "out",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "output",
                        "distribution": [{"kind": "shard", "axis": "x"}],
                    },
                ],
                "ops": [{"op": "elementwise_binary", "operator": "add", "lhs": "lhs", "rhs": "rhs", "out": "out"}],
            },
            "workload": _workload("bad_join", ["lhs", "rhs", "out"]),
        }
    )
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(canonical)

    with pytest.raises(ValueError, match="HTP.LAYOUT.DISTRIBUTION_INCOMPATIBLE"):
        build_type_layout_effects(kernel_ir, workload_ir, target={"backend": "generic", "option": "default"})


def test_sharded_output_requires_collective_discharge():
    pending = canonicalize_program(
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
                        "shape": ["N"],
                        "role": "input",
                        "distribution": [{"kind": "shard", "axis": "x"}],
                    },
                    {
                        "name": "out",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "output",
                        "distribution": [{"kind": "shard", "axis": "x"}],
                    },
                ],
                "ops": [{"op": "reshape", "source": "src", "out": "out"}],
            },
            "workload": _workload("collective_kernel", ["src", "out"]),
        }
    )
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(pending)

    with pytest.raises(ValueError, match="HTP.EFFECT.UNDISCHARGED_COLLECTIVE"):
        build_type_layout_effects(kernel_ir, workload_ir, target={"backend": "generic", "option": "default"})

    discharged = canonicalize_program(
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
                        "shape": ["N"],
                        "role": "input",
                        "distribution": [{"kind": "shard", "axis": "x"}],
                    },
                    {
                        "name": "out",
                        "kind": "buffer",
                        "dtype": "f32",
                        "shape": ["N"],
                        "role": "output",
                        "distribution": [{"kind": "shard", "axis": "x"}],
                    },
                ],
                "ops": [
                    {"op": "reshape", "source": "src", "out": "out"},
                    {"op": "allreduce", "source": "out", "out": "out"},
                ],
            },
            "workload": _workload("collective_kernel", ["src", "out"]),
        }
    )
    kernel_ir, workload_ir, _entities, _bindings = build_semantic_model(discharged)
    _types, _layout, effects = build_type_layout_effects(
        kernel_ir,
        workload_ir,
        target={"backend": "generic", "option": "default"},
    )

    assert effects["collectives"] == [
        {
            "collective_id": "op1.collective",
            "op_id": "op1",
            "kind": "allreduce",
            "outputs": ["out"],
            "status": "discharged",
            "discharged_by": "op1",
            "required_by": ["out"],
            "discharge_rule": "allreduce_over_sharded_output",
        }
    ]
