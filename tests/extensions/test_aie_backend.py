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
    analysis_index = json.loads(
        (package_dir / "ir" / "stages" / "s01" / "analysis" / "index.json").read_text()
    )
    analysis_paths = {item["analysis_id"]: item["path"] for item in analysis_index["analyses"]}
    assert analysis_paths == {
        "htp_ext.aie::MappingPlan@1": "ir/stages/s01/analysis/aie_mapping_plan.json",
        "htp_ext.aie::FIFOPlan@1": "ir/stages/s01/analysis/aie_fifo_plan.json",
    }
    mapping = json.loads((package_dir / "codegen" / "aie" / "mapping.json").read_text())
    fifos = json.loads((package_dir / "codegen" / "aie" / "fifos.json").read_text())
    assert mapping["tiles"] == [
        {"task_id": "task0", "kernel": "stream_add", "coords": [0, 0], "memory_space": "l2"}
    ]
    assert fifos["channels"] == [
        {
            "name": "fifo0",
            "dtype": "i32",
            "capacity": 0,
            "protocol": "fifo",
            "kind": "fifo",
            "producers": [],
            "consumers": [],
        }
    ]
    mlir_text = (package_dir / "codegen" / "aie" / "aie.mlir").read_text()
    assert 'aie.device("xdna2-npu1")' in mlir_text
    assert "%tile_0_0 = aie.tile(0, 0)" in mlir_text

    report = htp.bind(package_dir).validate()
    assert report.ok is True

    replay = htp.bind(package_dir).load(mode="sim").replay("s01")
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True

    build = htp.bind(package_dir).build(mode="device", force=True)
    assert build.ok is True
    assert build.built_outputs == [
        "build/aie/build_product.json",
        "build/aie/host_runtime.json",
    ]
    assert (package_dir / "build" / "aie" / "build_product.json").is_file()
    assert (package_dir / "build" / "aie" / "host_runtime.json").is_file()

    run = htp.bind(package_dir).load(mode="device").run("stream_add")
    assert run.ok is True
    assert run.result["entry"] == "stream_add"
    assert run.result["runtime"]["schema"] == "htp.aie.host_runtime.v1"
    assert run.result["runtime"]["entry"] == "stream_add"


def test_aie_extension_emits_objectfifos_from_process_channels(tmp_path):
    package_dir = tmp_path / "aie_pkg"
    package_dir.mkdir()

    emit_package(
        package_dir,
        program={
            "entry": "pipeline_demo",
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
                "entry": "pipeline_demo",
                "tasks": [
                    {"task_id": "p0", "kind": "process", "kernel": "stream_add", "args": []},
                    {"task_id": "p1", "kind": "process", "kernel": "stream_add", "args": []},
                ],
                "channels": [
                    {"name": "tiles", "dtype": "i32", "capacity": 2, "protocol": "fifo", "kind": "fifo"}
                ],
                "dependencies": [],
                "processes": [
                    {
                        "name": "producer",
                        "task_id": "p0",
                        "kernel": "stream_add",
                        "args": [],
                        "puts": [{"channel": "tiles", "count": 1}],
                        "gets": [],
                    },
                    {
                        "name": "consumer",
                        "task_id": "p1",
                        "kernel": "stream_add",
                        "args": [],
                        "puts": [],
                        "gets": [{"channel": "tiles", "count": 1}],
                    },
                ],
            },
        },
    )

    mapping = json.loads((package_dir / "codegen" / "aie" / "mapping.json").read_text())
    fifos = json.loads((package_dir / "codegen" / "aie" / "fifos.json").read_text())
    mlir_text = (package_dir / "codegen" / "aie" / "aie.mlir").read_text()

    assert [tile["task_id"] for tile in mapping["tiles"]] == ["p0", "p1"]
    assert fifos["channels"][0]["producers"] == [{"process": "producer", "task_id": "p0", "count": 1}]
    assert fifos["channels"][0]["consumers"] == [{"process": "consumer", "task_id": "p1", "count": 1}]
    assert "aie.objectfifo @tiles(%tile_0_0, {%tile_0_1}, 2 : i32)" in mlir_text


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


def test_aie_binding_reports_invalid_toolchain_manifest(tmp_path):
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
    toolchain_path = package_dir / "codegen" / "aie" / "toolchain.json"
    toolchain = json.loads(toolchain_path.read_text())
    toolchain["build_driver"] = {
        "kind": "python_module",
        "module": "broken.module",
        "callable": "build_package",
    }
    toolchain_path.write_text(json.dumps(toolchain, indent=2) + "\n")

    report = htp.bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.AIE_INVALID_TOOLCHAIN_MANIFEST",
            "detail": "AIE toolchain manifest must declare the reference build driver.",
        }
    ]


def test_aie_device_run_requires_built_runtime(tmp_path):
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

    run = htp.bind(package_dir).load(mode="device").run("stream_add")

    assert run.ok is False
    assert run.diagnostics == [
        {
            "code": "HTP.BINDINGS.AIE_RUN_ERROR",
            "detail": "AIE device run requires build/aie/host_runtime.json. Run build(mode='device') first.",
            "mode": "device",
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
