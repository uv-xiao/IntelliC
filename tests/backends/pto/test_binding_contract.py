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
