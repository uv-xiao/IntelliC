from __future__ import annotations

from htp.pipeline.defaults import run_default_pipeline
from htp.solver import available_pipeline_templates, solve_default_pipeline, solve_existing_package


def _vector_add_program() -> dict[str, object]:
    return {
        "entry": "vector_add",
        "kernel": {
            "name": "vector_add",
            "args": [
                {"name": "lhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                {"name": "rhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                {"name": "out", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "output"},
                {"name": "size", "kind": "scalar", "dtype": "i32", "role": "shape"},
            ],
            "ops": [
                {
                    "op": "elementwise_binary",
                    "operator": "add",
                    "lhs": "lhs",
                    "rhs": "rhs",
                    "out": "out",
                    "shape": ["size"],
                    "dtype": "f32",
                }
            ],
        },
        "workload": {
            "entry": "vector_add",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "vector_add",
                    "args": ["lhs", "rhs", "out", "size"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "analysis": {},
        "package": {"emitted": False},
        "target": {"backend": "pto", "option": "a2a3sim"},
    }


def test_solver_exposes_extension_template_candidates_when_requested():
    program = {
        "entry": "demo_kernel",
        "exprs": [
            {"target": "sum0", "op": "add", "lhs": "lhs", "rhs": "rhs"},
            {"target": "out", "op": "mul", "lhs": "sum0", "rhs": "scale"},
        ],
        "result": "out",
        "target": {"backend": "nvgpu", "option": "ampere"},
        "extensions": {"requested": ["htp_ext.mlir_cse"]},
    }

    templates = available_pipeline_templates(program=program)

    assert [template.template_id for template in templates] == [
        "htp.default.v1",
        "htp.default+htp_ext.mlir_cse.v1",
    ]


def test_solver_selects_extension_template_when_requested_and_eligible():
    program = {
        "entry": "demo_kernel",
        "exprs": [
            {"target": "sum0", "op": "add", "lhs": "lhs", "rhs": "rhs"},
            {"target": "out", "op": "mul", "lhs": "sum0", "rhs": "scale"},
        ],
        "result": "out",
        "target": {"backend": "nvgpu", "option": "ampere"},
        "extensions": {"requested": ["htp_ext.mlir_cse"]},
    }

    result = solve_default_pipeline(program=program)

    assert result.ok is True
    assert result.template_id == "htp.default+htp_ext.mlir_cse.v1"
    assert result.extension_results["htp_ext.mlir_cse"]["eligible"] is True


def test_solver_can_resume_from_existing_package(tmp_path):
    package_dir = tmp_path / "package"
    run_default_pipeline(package_dir=package_dir, program=_vector_add_program())

    result = solve_existing_package(package_dir)

    assert result.ok is True
    assert result.template_id == "htp.resume.v1"
    assert "Package.Emitted@1" in result.capabilities
    assert "Analysis.SchedulePlan@1" in result.state.analyses
