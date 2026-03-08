from __future__ import annotations

import json
from pathlib import Path

import pytest

from htp.pipeline.defaults import run_default_pipeline
from htp_ext.mlir_cse.import_ import import_program_from_module


def _eligible_kernel_program() -> dict[str, object]:
    return {
        "entry": "dup_expr_kernel",
        "kernel": {
            "name": "dup_expr_kernel",
            "args": [
                {"name": "lhs", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                {"name": "rhs", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                {"name": "scale", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
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
                {
                    "op": "elementwise_binary",
                    "operator": "mul",
                    "lhs": "sum1",
                    "rhs": "scale",
                    "out": "out",
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
                    "args": ["lhs", "rhs", "scale"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "analysis": {},
        "package": {"emitted": False},
        "target": {"backend": "nvgpu", "option": "ampere"},
        "extensions": {"requested": ["htp_ext.mlir_cse"]},
    }


def _stage_by_pass(manifest: dict[str, object], pass_id: str) -> dict[str, object]:
    for stage in manifest["stages"]["graph"]:
        if stage.get("pass") == pass_id:
            return stage
    raise AssertionError(f"missing stage for {pass_id}")


def test_run_default_pipeline_executes_mlir_extension_passes(tmp_path: Path):
    result = run_default_pipeline(package_dir=tmp_path / "pkg", program=_eligible_kernel_program())

    pass_ids = [stage.get("pass") for stage in result.stages if stage.get("pass")]

    assert "htp_ext.mlir_cse::export@1" in pass_ids
    assert "htp_ext.mlir_cse::import@1" in pass_ids


def test_mlir_extension_writes_full_roundtrip_artifact_set(tmp_path: Path):
    package_dir = tmp_path / "pkg"
    run_default_pipeline(package_dir=package_dir, program=_eligible_kernel_program())
    manifest = json.loads((package_dir / "manifest.json").read_text())

    export_stage = _stage_by_pass(manifest, "htp_ext.mlir_cse::export@1")
    import_stage = _stage_by_pass(manifest, "htp_ext.mlir_cse::import@1")
    export_dir = package_dir / export_stage["islands"][0]["dir"]
    import_dir = package_dir / import_stage["islands"][0]["dir"]

    assert (export_dir / "input.mlir").exists()
    assert (export_dir / "pipeline.txt").exists()
    assert (export_dir / "eligibility.json").exists()
    assert (export_dir / "ledger.json").exists()
    assert (import_dir / "output.mlir").exists()
    assert (import_dir / "import_summary.json").exists()
    assert (package_dir / "ir" / "stages" / import_stage["id"] / "maps" / "entity_map.json").exists()
    assert (package_dir / "ir" / "stages" / import_stage["id"] / "maps" / "binding_map.json").exists()

def test_mlir_extension_imports_transformed_output_mlir(tmp_path: Path):
    package_dir = tmp_path / "pkg"
    result = run_default_pipeline(package_dir=package_dir, program=_eligible_kernel_program())
    manifest = json.loads((package_dir / "manifest.json").read_text())

    import_stage = _stage_by_pass(manifest, "htp_ext.mlir_cse::import@1")
    kernel_ir = json.loads((package_dir / import_stage["semantic"]["kernel_ir"]).read_text())
    import_summary = json.loads(
        (package_dir / import_stage["islands"][0]["dir"] / "import_summary.json").read_text()
    )

    assert len(kernel_ir["ops"]) == 2
    assert len(import_summary["rewrites"]) == 1
    assert import_summary["rewrites"][0]["reused_target"] == "sum0"
    assert import_stage["id"] in {stage["id"] for stage in result.stages}


def test_mlir_extension_rejects_malformed_output_module():
    ledger = {
        "schema": "htp_ext.mlir_cse.ledger.v1",
        "entry": "dup_expr_kernel",
        "inputs": ["lhs", "rhs"],
        "result": "out",
        "ops": [
            {
                "mlir_result": "%v0",
                "target": "sum0",
                "op": "add",
                "lhs": "lhs",
                "rhs": "rhs",
                "entity_id": "dup_expr_kernel:E0",
            }
        ],
    }
    malformed_module = """module {\n  func.func @dup_expr_kernel(%lhs: i32, %rhs: i32) -> i32 {\n    return %missing : i32\n  }\n}\n"""

    with pytest.raises(ValueError, match="unknown SSA value"):
        import_program_from_module(malformed_module, ledger)


def test_mlir_extension_eligibility_rejects_protocol_heavy_program():
    from htp_ext.mlir_cse.export import eligibility_for

    program = {
        "entry": "channel_kernel",
        "kernel": {
            "name": "channel_kernel",
            "args": [
                {"name": "value", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                {"name": "channel", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
            ],
            "ops": [
                {"op": "channel_send", "value": "value", "channel": "channel", "outputs": []},
            ],
        },
        "workload": {
            "entry": "channel_kernel",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "channel_kernel",
                    "args": ["value", "channel"],
                }
            ],
            "channels": [{"name": "channel", "dtype": "i32", "capacity": 1, "protocol": "fifo"}],
            "dependencies": [],
            "processes": [{"name": "worker", "task_id": "task0", "kernel": "channel_kernel"}],
        },
    }

    eligibility = eligibility_for(program)

    assert eligibility["ok"] is False
    assert "typed.no_channels" in eligibility["failed_rules"]
    assert "typed.scalar_i32_only" in eligibility["satisfied_rules"]
    assert "typed.expr_program" in eligibility["failed_rules"]
