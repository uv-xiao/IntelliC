from htp.backends.pto.emit import emit_package
from htp.bindings.api import bind


def test_pto_build_returns_structured_result(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    result = bind(package_dir).build(mode="sim")

    assert result.ok is True
    assert result.mode == "sim"
    assert result.built_outputs == [
        "codegen/pto/kernel_config.py",
        "codegen/pto/pto_codegen.json",
        "build/toolchain.json",
    ]
    assert len(result.log_paths) == 1
    assert result.diagnostics == []


def test_pto_run_reports_external_toolchain_boundary(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["compute_tile"],
        },
    )

    session = bind(package_dir).load(mode="sim")
    result = session.run("demo_kernel")

    assert result.ok is False
    assert result.mode == "sim"
    assert result.entry == "demo_kernel"
    assert result.diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_RUN_REQUIRES_EXTERNAL_TOOLCHAIN",
            "detail": (
                "PTO package execution is owned by the external PTO toolchain; "
                "use replay(stage_id) for staged Python execution."
            ),
            "entry": "demo_kernel",
            "mode": "sim",
            "toolchain_manifest": "build/toolchain.json",
        }
    ]
    assert result.log_path is not None
