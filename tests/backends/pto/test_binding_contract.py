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
