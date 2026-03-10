from __future__ import annotations

from htp.pipeline.defaults import run_default_pipeline
from htp.solver import available_pipeline_templates, solve_default_pipeline, solve_existing_package
from tests.programs import pto_vector_dag_payload


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
    run_default_pipeline(package_dir=package_dir, program=pto_vector_dag_payload())

    result = solve_existing_package(package_dir)

    assert result.ok is True
    assert result.template_id == "htp.resume.v1"
    assert "Package.Emitted@1" in result.capabilities
    assert "Analysis.SchedulePlan@1" in result.state.analyses
