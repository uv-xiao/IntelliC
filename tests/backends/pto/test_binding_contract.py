import json

from htp.backends.pto.emit import emit_package
from htp.bindings.api import bind


def test_pto_binding_validates_required_files(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    binding = bind(package_dir)
    report = binding.validate()

    assert binding.__class__.__name__ == "PTOBinding"
    assert report.ok is True
    assert report.backend == "pto"
    assert report.variant == "a2a3sim"
    assert report.missing_files == []
    assert report.diagnostics == []


def test_pto_binding_reports_missing_required_files(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )
    (package_dir / "codegen" / "pto" / "kernel_config.py").unlink()
    (package_dir / "codegen" / "pto" / "pto_codegen.json").unlink()

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.missing_files == [
        "codegen/pto/kernel_config.py",
        "codegen/pto/pto_codegen.json",
    ]
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
            "detail": "Missing required PTO artifact path: codegen/pto/kernel_config.py",
        },
        {
            "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
            "detail": "Missing required PTO artifact path: codegen/pto/pto_codegen.json",
        },
    ]


def test_pto_binding_reports_manifest_pto_metadata_mismatch(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["extensions"]["pto"]["runtime_config"] = {
        "platform": "a2a3sim",
        "aicpu_thread_num": 8,
        "block_dim": 1,
    }
    manifest["extensions"]["pto"]["orchestration_entry"] = {
        "source": "orchestration/other.cpp",
        "function_name": "demo_kernel_orchestrate",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
            "detail": "manifest.json extensions.pto.runtime_config does not match kernel_config.py RUNTIME_CONFIG.",
            "manifest_field": "extensions.pto.runtime_config",
        },
        {
            "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
            "detail": "manifest.json extensions.pto.orchestration_entry does not match kernel_config.py ORCHESTRATION.",
            "manifest_field": "extensions.pto.orchestration_entry",
        },
    ]


def test_pto_binding_requires_manifest_pto_extension(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["extensions"]["pto"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
            "detail": "manifest.json extensions.pto is required for PTO packages.",
            "manifest_field": "extensions.pto",
        }
    ]


def test_pto_binding_requires_manifest_pto_contract_fields(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["extensions"]["pto"]["runtime_config"]
    del manifest["extensions"]["pto"]["orchestration_entry"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
            "detail": "manifest.json extensions.pto.runtime_config is required for PTO packages.",
            "manifest_field": "extensions.pto.runtime_config",
        },
        {
            "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
            "detail": "manifest.json extensions.pto.orchestration_entry is required for PTO packages.",
            "manifest_field": "extensions.pto.orchestration_entry",
        },
    ]


def test_pto_binding_requires_manifest_outputs_contract_fields(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["outputs"]["kernel_config"]
    del manifest["outputs"]["pto_codegen_index"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
            "detail": "manifest.json outputs.kernel_config is required for PTO packages.",
            "manifest_field": "outputs.kernel_config",
        },
        {
            "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
            "detail": "manifest.json outputs.pto_codegen_index is required for PTO packages.",
            "manifest_field": "outputs.pto_codegen_index",
        },
    ]


def test_pto_binding_requires_manifest_pto_kernel_project_dir(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["extensions"]["pto"]["kernel_project_dir"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
            "detail": "manifest.json extensions.pto.kernel_project_dir is required for PTO packages.",
            "manifest_field": "extensions.pto.kernel_project_dir",
        }
    ]


def test_pto_binding_reports_target_and_codegen_metadata_mismatch(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["target"]["variant"] = "a2a3"
    manifest["target"]["hardware_profile"] = "ascend:a2a3"
    manifest["extensions"]["pto"]["platform"] = "a2a3sim"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    codegen_index_path = package_dir / "codegen" / "pto" / "pto_codegen.json"
    codegen_index = json.loads(codegen_index_path.read_text())
    codegen_index["backend"] = "other-backend"
    codegen_index["variant"] = "a2a3sim"
    codegen_index_path.write_text(json.dumps(codegen_index, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
            "detail": "PTO metadata backend does not agree across manifest target and pto_codegen.json.",
            "field": "backend",
            "manifest_field": "target.backend",
            "codegen_field": "codegen/pto/pto_codegen.json.backend",
            "manifest_value": "pto",
            "codegen_value": "other-backend",
        },
        {
            "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
            "detail": "PTO metadata variant/platform does not agree across manifest target, manifest extensions, kernel_config.py, and pto_codegen.json.",
            "field": "variant",
            "manifest_field": "target.variant",
            "extension_field": "extensions.pto.platform",
            "kernel_config_field": "kernel_config.py:RUNTIME_CONFIG.platform",
            "codegen_field": "codegen/pto/pto_codegen.json.variant",
            "manifest_value": "a2a3",
            "extension_value": "a2a3sim",
            "kernel_config_value": "a2a3sim",
            "codegen_value": "a2a3sim",
        },
    ]


def test_pto_binding_reports_kernel_platform_and_hardware_profile_mismatch(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["target"]["hardware_profile"] = "ascend:wrong"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    kernel_config_path = package_dir / "codegen" / "pto" / "kernel_config.py"
    kernel_config_path.write_text(
        kernel_config_path.read_text().replace("'platform': 'a2a3sim'", "'platform': 'a2a3'")
    )

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
            "detail": "PTO metadata hardware_profile does not agree with target.variant.",
            "field": "hardware_profile",
            "manifest_field": "target.hardware_profile",
            "manifest_value": "ascend:wrong",
            "expected_value": "ascend:a2a3sim",
        },
        {
            "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
            "detail": "PTO metadata variant/platform does not agree across manifest target, manifest extensions, kernel_config.py, and pto_codegen.json.",
            "field": "variant",
            "manifest_field": "target.variant",
            "extension_field": "extensions.pto.platform",
            "kernel_config_field": "kernel_config.py:RUNTIME_CONFIG.platform",
            "codegen_field": "codegen/pto/pto_codegen.json.variant",
            "manifest_value": "a2a3sim",
            "extension_value": "a2a3sim",
            "kernel_config_value": "a2a3",
            "codegen_value": "a2a3sim",
        },
    ]
