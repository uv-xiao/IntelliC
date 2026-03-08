from __future__ import annotations

import json

from htp.compiler import compile_program
from htp.tools import explain_diagnostic, replay_package, semantic_diff, verify_package


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
    assert replay.stage_id == "s06"
    assert replay.result["package"]["emitted"] is True


def test_verify_package_records_agent_provenance(tmp_path):
    package_dir = tmp_path / "pto_pkg"
    compile_program(package_dir=package_dir, target="pto-a2a3sim", program=_vector_add_program())

    report = verify_package(package_dir, goal="regression-check")

    assert report["ok"] is True
    assert report["gates"] == {"validate": True, "replay": True}
    manifest = json.loads((package_dir / "manifest.json").read_text())
    assert manifest["extensions"]["agent"]["goal"] == "regression-check"
    assert manifest["extensions"]["agent"]["gates"] == {"validate": True, "replay": True}
    assert manifest["extensions"]["agent"]["evidence"]["replay_log"] == report["evidence"]["replay_log"]


def test_semantic_diff_reports_manifest_and_semantic_changes(tmp_path):
    left_dir = tmp_path / "pto_pkg"
    right_dir = tmp_path / "nvgpu_pkg"
    compile_program(package_dir=left_dir, target="pto-a2a3sim", program=_vector_add_program())
    compile_program(package_dir=right_dir, target="nvgpu-ampere", program=_matmul_program())

    diff = semantic_diff(left_dir, right_dir)

    assert diff["equal"] is False
    assert "manifest.target" in diff["changed_sections"]
    assert "current_stage.kernel_ir" in diff["changed_sections"]
    assert diff["stage_ids"] == {"left": "s06", "right": "s06"}


def test_explain_diagnostic_returns_contract_reference():
    explanation = explain_diagnostic("HTP.BINDINGS.MISSING_CONTRACT_FILE")

    assert explanation["code"] == "HTP.BINDINGS.MISSING_CONTRACT_FILE"
    assert explanation["known"] is True
    assert explanation["title"] == "Missing contract artifact"
    assert explanation["fix_hint_policy"] == "rebuild_or_validate_artifacts"
    assert "docs/design/impls/07_binding_interface.md" in explanation["docs"]


def test_explain_diagnostic_returns_generic_fallback_for_unknown_code():
    explanation = explain_diagnostic("HTP.UNKNOWN.CODE")

    assert explanation["code"] == "HTP.UNKNOWN.CODE"
    assert explanation["known"] is False
    assert explanation["fix_hint_policy"] == "inspect_diagnostic_payload"
