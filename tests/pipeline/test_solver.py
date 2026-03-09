from __future__ import annotations

import json

from htp.backends.nvgpu.declarations import declaration_for as nvgpu_declaration_for
from htp.backends.pto.declarations import declaration_for as pto_declaration_for
from htp.passes.contracts import PassContract
from htp.pipeline.defaults import MANDATORY_PASS_IDS
from htp.solver import (
    PipelineTemplate,
    available_pipeline_templates,
    default_pipeline_template,
    solve_default_pipeline,
    solve_pipeline,
    validate_final_artifacts,
)


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


def _matmul_program() -> dict[str, object]:
    return {
        "entry": "matmul_demo",
        "kernel": {
            "name": "matmul_demo",
            "args": [
                {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
                {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
                {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
                {"name": "M", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "N", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "K", "kind": "scalar", "dtype": "i32", "role": "shape"},
            ],
            "ops": [
                {
                    "op": "matmul",
                    "lhs": "A",
                    "rhs": "B",
                    "out": "C",
                    "dtype": "f32",
                    "shape": ["M", "N", "K"],
                }
            ],
        },
        "workload": {
            "entry": "matmul_demo",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "matmul_demo",
                    "args": ["A", "B", "C", "M", "N", "K"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "analysis": {},
        "package": {"emitted": False},
        "target": {"backend": "nvgpu", "option": "ampere"},
    }


def test_solver_accepts_default_pipeline_and_tracks_capabilities():
    result = solve_default_pipeline(program=_vector_add_program())

    assert result.ok is True
    assert result.template_id == "htp.default.v1"
    assert result.pass_ids == list(MANDATORY_PASS_IDS)
    assert "Package.Emitted@1" in result.capabilities
    assert result.extension_results == {}


def test_default_pipeline_uses_backend_required_outputs():
    pto_template = default_pipeline_template(target={"backend": "pto", "option": "a2a3sim"})
    nvgpu_template = default_pipeline_template(target={"backend": "nvgpu", "option": "ampere"})

    assert pto_template.required_outputs == pto_declaration_for("a2a3sim").required_outputs
    assert nvgpu_template.required_outputs == nvgpu_declaration_for("ampere").required_outputs


def test_backend_declarations_define_handler_support_contract():
    assert "matmul" in nvgpu_declaration_for("ampere").supported_ops
    assert "matmul" not in pto_declaration_for("a2a3sim").supported_ops

    result = solve_default_pipeline(program=_matmul_program())

    assert result.ok is True


def test_solver_reports_missing_capability():
    template = PipelineTemplate(
        template_id="test.missing_cap.v1",
        passes=(
            PassContract(
                pass_id="test::requires_missing@1",
                owner="test",
                kind="transform",
                ast_effect="preserves",
                requires=("Missing.Capability@1",),
            ),
        ),
        required_outputs=(),
    )

    result = solve_pipeline(program=_vector_add_program(), template=template)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.failed_at_pass == "test::requires_missing@1"
    assert result.failure.missing_caps == ("Missing.Capability@1",)


def test_solver_reports_missing_layout_and_effect_invariants():
    template = PipelineTemplate(
        template_id="test.missing_invariants.v1",
        passes=(
            PassContract(
                pass_id="test::requires_invariants@1",
                owner="test",
                kind="transform",
                ast_effect="preserves",
                requires_layout_invariants=("Layout.Typed@1",),
                requires_effect_invariants=("Effects.Typed@1",),
            ),
        ),
        required_outputs=(),
    )

    result = solve_pipeline(program=_vector_add_program(), template=template)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.failed_at_pass == "test::requires_invariants@1"
    assert result.failure.missing_caps == ("Layout.Typed@1", "Effects.Typed@1")


def test_solver_reports_stale_analysis_after_invalidation():
    template = PipelineTemplate(
        template_id="test.analysis_invalidated.v1",
        passes=(
            PassContract.analysis(
                pass_id="test::produce_analysis@1",
                owner="test",
                provides=("Analysis.SchedulePlan@1",),
            ),
            PassContract(
                pass_id="test::invalidate_analysis@1",
                owner="test",
                kind="transform",
                ast_effect="mutates",
                invalidates=("Analysis.SchedulePlan@1",),
            ),
            PassContract(
                pass_id="test::consume_analysis@1",
                owner="test",
                kind="analysis",
                ast_effect="preserves",
                requires=("Analysis.SchedulePlan@1",),
                analysis_requires=("Analysis.SchedulePlan@1",),
            ),
        ),
        required_outputs=(),
    )

    result = solve_pipeline(program=_vector_add_program(), template=template)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.failed_at_pass == "test::consume_analysis@1"
    assert result.failure.missing_caps == ("Analysis.SchedulePlan@1",)
    assert result.failure.analysis_requirements == ("Analysis.SchedulePlan@1",)


def test_solver_reports_missing_backend_handler():
    program = _vector_add_program()
    program["target"] = {"backend": "pto", "option": "a2a3sim"}
    program["kernel"] = {
        "name": "channel_kernel",
        "args": [
            {"name": "value", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
            {"name": "channel", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
        ],
        "ops": [
            {"op": "channel_send", "value": "value", "channel": "channel", "outputs": []},
        ],
    }
    program["workload"] = {
        "entry": "channel_kernel",
        "tasks": [
            {
                "task_id": "task0",
                "kind": "kernel_call",
                "kernel": "channel_kernel",
                "args": ["value", "channel"],
            }
        ],
        "channels": [{"name": "channel", "dtype": "i32"}],
        "dependencies": [],
    }

    result = solve_default_pipeline(program=program)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.failed_at_pass == "target.handlers"
    assert result.failure.missing_handlers == ({"backend": "pto", "op": "channel_send"},)


def test_solver_writes_failure_report_for_missing_final_artifact(tmp_path):
    result = solve_default_pipeline(program=_vector_add_program())

    artifact_check = validate_final_artifacts(tmp_path, result)

    assert artifact_check.ok is False
    assert artifact_check.failure is not None
    assert artifact_check.failure.failed_at_pass == "final_contract"
    report = json.loads((tmp_path / "ir" / "solver_failure.json").read_text())
    assert report["artifact_contract_violations"] == [
        "codegen/pto/kernel_config.py",
        "codegen/pto/pto_codegen.json",
        "build/toolchain.json",
    ]


def test_available_pipeline_templates_expand_bounded_choices():
    template = PipelineTemplate(
        template_id="test.or.v1",
        passes=(),
        pass_choices=(
            (
                PassContract.analysis(pass_id="test::a@1", owner="test"),
                PassContract.analysis(pass_id="test::b@1", owner="test"),
            ),
        ),
    )

    from htp.solver import _expand_template_choices

    expanded = _expand_template_choices(template)

    assert [item.template_id for item in expanded] == [
        "test.or.v1+choice0:test::a@1",
        "test.or.v1+choice0:test::b@1",
    ]
    assert [[contract.pass_id for contract in item.passes] for item in expanded] == [
        ["test::a@1"],
        ["test::b@1"],
    ]


def test_solver_uses_extension_registry_for_templates():
    program = {
        "entry": "dup_expr_kernel",
        "kernel": {
            "name": "dup_expr_kernel",
            "args": [
                {"name": "lhs", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                {"name": "rhs", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
            ],
            "ops": [
                {
                    "op": "elementwise_binary",
                    "operator": "add",
                    "lhs": "lhs",
                    "rhs": "rhs",
                    "out": "sum0",
                    "shape": [],
                    "dtype": "i32",
                },
                {
                    "op": "elementwise_binary",
                    "operator": "add",
                    "lhs": "lhs",
                    "rhs": "rhs",
                    "out": "sum1",
                    "shape": [],
                    "dtype": "i32",
                },
            ],
        },
        "workload": {
            "entry": "dup_expr_kernel",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "dup_expr_kernel",
                    "args": ["lhs", "rhs"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "target": {"backend": "nvgpu", "option": "ampere"},
        "extensions": {"requested": ["htp_ext.mlir_cse"]},
    }

    templates = available_pipeline_templates(program=program)

    assert any(template.template_id == "htp.default+htp_ext.mlir_cse.v1" for template in templates)


def test_solver_exposes_mlir_cse_extension_eligibility():
    result = solve_default_pipeline(
        program={
            "entry": "expr_kernel",
            "exprs": [
                {"target": "sum0", "op": "add", "lhs": "lhs", "rhs": "rhs"},
                {"target": "out", "op": "mul", "lhs": "sum0", "rhs": "scale"},
            ],
            "result": "out",
            "extensions": {"requested": ["htp_ext.mlir_cse"]},
            "target": {"backend": "nvgpu", "option": "ampere"},
        }
    )

    assert result.ok is True
    assert result.extension_results["htp_ext.mlir_cse"]["eligible"] is True
    assert result.extension_results["htp_ext.mlir_cse"]["provides"] == ["Extension.MLIRCSEEligible@1"]
