from __future__ import annotations

import json

import htp
from htp_ext.aie import emit_package


def test_aie_extension_emits_artifact_contract_and_replays(tmp_path):
    package_dir = tmp_path / "aie_pkg"
    package_dir.mkdir()

    manifest = emit_package(
        package_dir,
        program={
            "entry": "stream_add",
            "kernel": {
                "name": "stream_add",
                "args": [
                    {"name": "tile_in", "kind": "buffer", "dtype": "i32", "shape": ["size"], "role": "input"},
                    {
                        "name": "tile_out",
                        "kind": "buffer",
                        "dtype": "i32",
                        "shape": ["size"],
                        "role": "output",
                    },
                    {"name": "size", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
                ],
                "ops": [
                    {
                        "op": "elementwise_binary",
                        "operator": "add",
                        "lhs": "tile_in",
                        "rhs": "tile_in",
                        "out": "tile_out",
                        "shape": ["size"],
                        "dtype": "i32",
                    }
                ],
            },
            "workload": {
                "entry": "stream_add",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "stream_add",
                        "args": ["tile_in", "tile_out", "size"],
                    }
                ],
                "channels": [{"name": "fifo0", "dtype": "i32", "kind": "fifo"}],
                "dependencies": [],
            },
        },
        profile="xdna2-npu1",
    )

    assert manifest["target"] == {
        "backend": "aie",
        "variant": "mlir-aie",
        "hardware_profile": "amd-xdna2:xdna2-npu1",
    }
    assert manifest["outputs"] == {
        "aie_codegen_index": "codegen/aie/aie_codegen.json",
        "toolchain_manifest": "codegen/aie/toolchain.json",
    }
    assert manifest["extensions"]["aie"]["mlir"] == "codegen/aie/aie.mlir"
    assert manifest["extensions"]["aie"]["toolchain_manifest"] == "codegen/aie/toolchain.json"
    assert (package_dir / "codegen" / "aie" / "aie.mlir").is_file()
    assert (package_dir / "codegen" / "aie" / "mapping.json").is_file()
    assert (package_dir / "codegen" / "aie" / "fifos.json").is_file()
    assert (package_dir / "codegen" / "aie" / "toolchain.json").is_file()
    assert (package_dir / "codegen" / "aie" / "aie_codegen.json").is_file()

    report = htp.bind(package_dir).validate()
    assert report.ok is True

    replay = htp.bind(package_dir).load(mode="sim").replay("s01")
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True


def test_aie_binding_reports_missing_mlir_artifact(tmp_path):
    package_dir = tmp_path / "aie_pkg"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "stream_add",
            "kernel": {"name": "stream_add", "args": [], "ops": []},
            "workload": {"entry": "stream_add", "tasks": [], "channels": [], "dependencies": []},
        },
    )
    (package_dir / "codegen" / "aie" / "aie.mlir").unlink()

    report = htp.bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.AIE_MISSING_CONTRACT_FILE",
            "detail": "Missing required AIE artifact path: codegen/aie/aie.mlir",
        }
    ]


def test_aie_binding_reports_output_contract_mismatch(tmp_path):
    package_dir = tmp_path / "aie_pkg"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "stream_add",
            "kernel": {"name": "stream_add", "args": [], "ops": []},
            "workload": {"entry": "stream_add", "tasks": [], "channels": [], "dependencies": []},
        },
    )
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["outputs"]["toolchain_manifest"] = "wrong/toolchain.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = htp.bind(package_dir).validate()

    assert report.ok is False
    assert {
        "code": "HTP.BINDINGS.AIE_METADATA_MISMATCH",
        "detail": "manifest.json outputs.toolchain_manifest must use the canonical AIE artifact path.",
        "manifest_field": "outputs.toolchain_manifest",
        "manifest_value": "wrong/toolchain.json",
        "expected_value": "codegen/aie/toolchain.json",
    } in report.diagnostics
