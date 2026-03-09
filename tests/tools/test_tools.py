from __future__ import annotations

import json

from htp.agent_policy import load_agent_policy
from htp.compiler import compile_program
from htp.pipeline.defaults import MANDATORY_PASS_IDS
from htp.tools import (
    bisect_stages,
    explain_diagnostic,
    minimize_package,
    promotion_plan,
    replay_package,
    semantic_diff,
    verify_package,
)
from tests.conftest import copy_golden_fixture


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
    }


def _matmul_program() -> dict[str, object]:
    return {
        "entry": "gemm_tile",
        "kernel": {
            "name": "gemm_tile",
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
                    "m": "M",
                    "n": "N",
                    "k": "K",
                    "dtype": "f32",
                }
            ],
        },
        "workload": {
            "entry": "gemm_tile",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "gemm_tile",
                    "args": ["A", "B", "C", "M", "N", "K"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "analysis": {},
        "package": {"emitted": False},
    }


def test_replay_package_replays_current_stage(tmp_path):
    package_dir = tmp_path / "pto_pkg"
    compile_program(package_dir=package_dir, target="pto-a2a3sim", program=_vector_add_program())

    replay = replay_package(package_dir)

    assert replay.ok is True
    assert replay.stage_id == f"s{len(MANDATORY_PASS_IDS):02d}"
    assert replay.result["package"]["emitted"] is True


def test_verify_package_records_agent_provenance(tmp_path):
    package_dir = tmp_path / "pto_pkg"
    compile_program(package_dir=package_dir, target="pto-a2a3sim", program=_vector_add_program())

    report = verify_package(package_dir, goal="regression-check")

    assert report["ok"] is True
    assert report["gates"] == {"validate": True, "replay": True, "target_suite": True}
    manifest = json.loads((package_dir / "manifest.json").read_text())
    assert manifest["extensions"]["agent"]["goal"] == "regression-check"
    assert manifest["extensions"]["agent"]["gates"] == {
        "validate": True,
        "replay": True,
        "target_suite": True,
    }
    assert manifest["extensions"]["agent"]["evidence"]["replay_log"] == report["evidence"]["replay_log"]
    assert manifest["extensions"]["agent"]["promotion"]["allowed"] is True


def test_semantic_diff_reports_manifest_and_semantic_changes(tmp_path):
    left_dir = tmp_path / "pto_pkg"
    right_dir = tmp_path / "nvgpu_pkg"
    compile_program(package_dir=left_dir, target="pto-a2a3sim", program=_vector_add_program())
    compile_program(package_dir=right_dir, target="nvgpu-ampere", program=_matmul_program())

    diff = semantic_diff(left_dir, right_dir)

    assert diff["equal"] is False
    assert "manifest.target" in diff["changed_sections"]
    assert "current_stage.kernel_ir" in diff["changed_sections"]
    expected_stage = f"s{len(MANDATORY_PASS_IDS):02d}"
    assert diff["stage_ids"] == {"left": expected_stage, "right": expected_stage}
    assert "details" in diff
    assert "current_stage.kernel_ir" in diff["details"]
    assert diff["details"]["current_stage.kernel_ir"]["refs"]["left"].endswith("/kernel_ir.json")
    assert diff["details"]["current_stage.kernel_ir"]["refs"]["right"].endswith("/kernel_ir.json")
    assert "current_stage.identity" in diff["details"]
    assert diff["details"]["current_stage.identity"]["details"]["refs"]["left"]["entities"].endswith(
        "/ids/entities.json"
    )
    assert diff["details"]["current_stage.identity"]["details"]["entity_blame"]["right_added"]
    assert diff["details"]["current_stage.identity"]["details"]["entity_blame"]["right_added"][0]["node_ids"]


def test_semantic_diff_reports_pass_trace_refs(tmp_path):
    left_dir = tmp_path / "left_pkg"
    right_dir = tmp_path / "right_pkg"
    compile_program(package_dir=left_dir, target="pto-a2a3sim", program=_vector_add_program())
    compile_program(package_dir=right_dir, target="pto-a2a3sim", program=_vector_add_program())
    trace_path = right_dir / "ir" / "pass_trace.jsonl"
    trace_path.write_text(trace_path.read_text() + json.dumps({"schema": "htp.pass_trace_event.v1"}) + "\n")

    diff = semantic_diff(left_dir, right_dir)

    assert "pass_trace" in diff["changed_sections"]
    assert diff["details"]["pass_trace"]["details"]["refs"] == {
        "left": "ir/pass_trace.jsonl",
        "right": "ir/pass_trace.jsonl",
    }


def test_semantic_diff_reports_replay_stub_refs(tmp_path):
    left_dir = copy_golden_fixture("nvgpu_demo", tmp_path / "left")
    right_dir = copy_golden_fixture("nvgpu_demo", tmp_path / "right")
    stubs_path = right_dir / "ir" / "stages" / "s02" / "replay" / "stubs.json"
    stubs = json.loads(stubs_path.read_text())
    stubs["stubs"][0]["reason"] = "intentionally_unimplemented"
    stubs_path.write_text(json.dumps(stubs, indent=2) + "\n")

    diff = semantic_diff(left_dir, right_dir, left_stage_id="s02", right_stage_id="s02")

    assert "current_stage.replay_stubs" in diff["changed_sections"]
    assert diff["details"]["current_stage.replay_stubs"]["details"]["refs"]["right"].endswith(
        "/replay/stubs.json"
    )


def test_explain_diagnostic_returns_contract_reference():
    explanation = explain_diagnostic("HTP.BINDINGS.MISSING_CONTRACT_FILE")

    assert explanation["code"] == "HTP.BINDINGS.MISSING_CONTRACT_FILE"
    assert explanation["known"] is True
    assert explanation["title"] == "Missing contract artifact"
    assert explanation["fix_hint_policy"] == "rebuild_or_validate_artifacts"
    assert "docs/design/layers/04_artifacts_replay_debug.md" in explanation["docs"]


def test_explain_diagnostic_uses_family_catalog_for_protocol_codes():
    explanation = explain_diagnostic("HTP.PROTOCOL.UNBALANCED_CHANNEL")

    assert explanation["code"] == "HTP.PROTOCOL.UNBALANCED_CHANNEL"
    assert explanation["known"] is True
    assert explanation["matched_by"] == "family"
    assert explanation["fix_hint_policy"] == "repair_protocol_obligations"
    assert "examples/patterns/csp/channel_pipeline/README.md" in explanation["docs"]


def test_explain_diagnostic_uses_replay_family_catalog():
    explanation = explain_diagnostic("HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY")

    assert explanation["code"] == "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY"
    assert explanation["known"] is True
    assert explanation["matched_by"] == "family"
    assert explanation["fix_hint_policy"] == "inspect_replay_stub_and_stage_evidence"
    assert "docs/design/layers/04_artifacts_replay_debug.md" in explanation["docs"]


def test_explain_diagnostic_returns_generic_fallback_for_unknown_code():
    explanation = explain_diagnostic("HTP.UNKNOWN.CODE")

    assert explanation["code"] == "HTP.UNKNOWN.CODE"
    assert explanation["known"] is False
    assert explanation["fix_hint_policy"] == "inspect_diagnostic_payload"


def test_load_agent_policy_reads_toml_file(tmp_path):
    policy_path = tmp_path / "agent_policy.toml"
    policy_path.write_text(
        "\n".join(
            (
                "[agent]",
                'allowed_edit_roots = ["htp", "docs"]',
                'required_gates = ["validate", "replay", "golden_diff"]',
                'promotion_mode = "pr"',
                "",
                "[perf]",
                "enabled = true",
                "max_regression_pct = 3.5",
                "",
            )
        )
    )

    policy = load_agent_policy(policy_path)

    assert policy["agent"]["allowed_edit_roots"] == ["htp", "docs"]
    assert policy["agent"]["required_gates"] == ["validate", "replay", "golden_diff"]
    assert "passes" in policy["agent"]["edit_corridor_templates"]
    assert policy["perf"]["enabled"] is True
    assert policy["perf"]["max_regression_pct"] == 3.5


def test_verify_package_can_enforce_golden_diff_gate(tmp_path):
    package_dir = copy_golden_fixture("pto_demo", tmp_path)
    golden_dir = copy_golden_fixture("pto_demo", tmp_path / "golden")

    report = verify_package(package_dir, goal="golden-check", golden_package_dir=golden_dir)

    assert report["ok"] is True
    assert report["gates"]["golden_diff"] is True
    assert report["gates"]["target_suite"] is True
    assert report["evidence"]["golden_diff"]["equal"] is True


def test_verify_package_can_emit_promotion_plan_and_perf_gate(tmp_path):
    package_dir = copy_golden_fixture("nvgpu_demo", tmp_path)
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    copy_golden_fixture("nvgpu_demo", baseline_dir)

    perf_dir = package_dir / "metrics"
    perf_dir.mkdir()
    (perf_dir / "perf.json").write_text(json.dumps({"runtime_ms": 10.0}) + "\n")
    baseline_perf_dir = baseline_dir / "nvgpu_demo" / "metrics"
    baseline_perf_dir.mkdir()
    (baseline_perf_dir / "perf.json").write_text(json.dumps({"runtime_ms": 9.8}) + "\n")

    policy_path = tmp_path / "agent_policy.toml"
    policy_path.write_text(
        "\n".join(
            (
                "[agent]",
                'required_gates = ["validate", "replay", "target_suite", "perf"]',
                'promotion_mode = "pr"',
                "",
                "[perf]",
                "enabled = true",
                "max_regression_pct = 5.0",
                "",
            )
        )
    )

    report = verify_package(
        package_dir,
        goal="perf-check",
        perf_baseline_dir=baseline_dir / "nvgpu_demo",
        policy_path=policy_path,
    )

    assert report["gates"]["perf"] is True
    assert report["promotion"]["allowed"] is True
    assert report["promotion"]["mode"] == "pr"


def test_promotion_plan_holds_when_required_gate_fails(tmp_path):
    package_dir = copy_golden_fixture("pto_demo", tmp_path)
    policy_path = tmp_path / "agent_policy.toml"
    policy_path.write_text(
        "\n".join(
            (
                "[agent]",
                'required_gates = ["validate", "replay", "golden_diff"]',
                'promotion_mode = "auto-land"',
                "",
            )
        )
    )

    plan = promotion_plan(package_dir, policy_path=policy_path)

    assert plan["allowed"] is False
    assert plan["next_action"] == "hold"
    assert plan["failed_required_gates"] == ["golden_diff"]


def test_bisect_stages_reports_first_divergent_stage(tmp_path):
    left_dir = tmp_path / "left_pkg"
    right_dir = tmp_path / "right_pkg"
    compile_program(package_dir=left_dir, target="nvgpu-ampere", program=_vector_add_program())
    compile_program(package_dir=right_dir, target="nvgpu-ampere", program=_vector_add_program())
    manifest = json.loads((right_dir / "manifest.json").read_text())
    current_stage = manifest["stages"]["current"]
    kernel_ir_path = (
        right_dir
        / next(stage for stage in manifest["stages"]["graph"] if stage["id"] == current_stage)["semantic"][
            "kernel_ir"
        ]
    )
    kernel_ir = json.loads(kernel_ir_path.read_text())
    kernel_ir["ops"][0]["attrs"]["operator"] = "mul"
    kernel_ir_path.write_text(json.dumps(kernel_ir, indent=2) + "\n")

    result = bisect_stages(left_dir, right_dir)

    assert result["equal"] is False
    expected_stage = f"s{len(MANDATORY_PASS_IDS):02d}"
    assert result["first_divergent_stage"] == {"left": expected_stage, "right": expected_stage}
    assert "current_stage.kernel_ir" in result["reason"]["changed_sections"]


def test_minimize_package_keeps_prefix_through_selected_stage(tmp_path):
    package_dir = tmp_path / "nvgpu_pkg"
    compile_program(package_dir=package_dir, target="nvgpu-ampere", program=_matmul_program())

    minimized_dir = tmp_path / "minimized"
    result = minimize_package(package_dir, minimized_dir, stage_id="s03")

    assert result["stage_id"] == "s03"
    assert result["output_dir"] == str(minimized_dir)
    manifest = json.loads((minimized_dir / "manifest.json").read_text())
    assert manifest["stages"]["current"] == "s03"
    assert [stage["id"] for stage in manifest["stages"]["graph"]] == ["s00", "s01", "s02", "s03"]
