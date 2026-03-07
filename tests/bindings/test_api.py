from contextlib import contextmanager
import json
import importlib
import sys


def _write_manifest(package_dir):
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "htp.manifest.v1",
                "target": {
                    "backend": "pto",
                    "variant": "a2a3sim",
                },
                "stages": {
                    "current": "s00",
                    "graph": [],
                },
            },
            indent=2,
        )
        + "\n"
    )


@contextmanager
def _import_fresh_htp():
    saved_modules = {
        module_name: module
        for module_name, module in sys.modules.items()
        if module_name == "htp" or module_name.startswith("htp.")
    }
    for module_name in list(saved_modules):
        sys.modules.pop(module_name, None)
    try:
        yield importlib.import_module("htp")
    finally:
        for module_name in list(sys.modules):
            if module_name == "htp" or module_name.startswith("htp."):
                sys.modules.pop(module_name, None)
        sys.modules.update(saved_modules)


def test_bind_returns_binding_for_manifest_backend(tmp_path):
    with _import_fresh_htp() as htp:
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        _write_manifest(package_dir)

        binding = htp.bind(package_dir)

        assert binding.backend == "pto"
        assert binding.variant == "a2a3sim"

        report = binding.validate()
        assert report.ok is False
        assert report.backend == "pto"
        assert report.variant == "a2a3sim"
        assert report.missing_files == [
            "codegen/pto/kernel_config.py",
            "codegen/pto/pto_codegen.json",
            "build/toolchain.json",
        ]
        assert report.diagnostics == [
            {
                "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
                "detail": "manifest.json target.hardware_profile is required for PTO packages.",
                "manifest_field": "target.hardware_profile",
            },
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
            {
                "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
                "detail": "manifest.json outputs.toolchain_manifest is required for PTO packages.",
                "manifest_field": "outputs.toolchain_manifest",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
                "detail": "manifest.json extensions.pto is required for PTO packages.",
                "manifest_field": "extensions.pto",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
                "detail": "Missing required PTO artifact path: codegen/pto/kernel_config.py",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
                "detail": "Missing required PTO artifact path: codegen/pto/pto_codegen.json",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
                "detail": "Missing required PTO artifact path: build/toolchain.json",
            },
        ]


def test_load_returns_normalized_load_result_shape(tmp_path):
    with _import_fresh_htp():
        from htp.bindings.api import bind as bind_api

        package_dir = tmp_path / "package"
        package_dir.mkdir()
        _write_manifest(package_dir)

        session = bind_api(package_dir).load(mode="sim")

        assert session.__class__.__name__ == "LoadResult"
        assert session.ok is False
        assert session.mode == "sim"
        assert session.backend == "pto"
        assert session.variant == "a2a3sim"
        assert session.diagnostics == [
            {
                "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
                "detail": "manifest.json target.hardware_profile is required for PTO packages.",
                "manifest_field": "target.hardware_profile",
            },
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
            {
                "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
                "detail": "manifest.json outputs.toolchain_manifest is required for PTO packages.",
                "manifest_field": "outputs.toolchain_manifest",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
                "detail": "manifest.json extensions.pto is required for PTO packages.",
                "manifest_field": "extensions.pto",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
                "detail": "Missing required PTO artifact path: codegen/pto/kernel_config.py",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
                "detail": "Missing required PTO artifact path: codegen/pto/pto_codegen.json",
            },
            {
                "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
                "detail": "Missing required PTO artifact path: build/toolchain.json",
            },
        ]


def test_load_rejects_mode_platform_mismatch(tmp_path):
    with _import_fresh_htp():
        from htp.backends.pto.emit import emit_package
        from htp.bindings.api import bind as bind_api

        package_dir = tmp_path / "package"
        package_dir.mkdir()
        emit_package(
            package_dir,
            program={
                "entry": "demo_kernel",
                "ops": ["compute_tile"],
            },
            variant="a2a3sim",
        )

        session = bind_api(package_dir).load(mode="device")

        assert session.ok is False
        assert session.diagnostics == [
            {
                "code": "HTP.BINDINGS.PTO_MODE_PLATFORM_MISMATCH",
                "detail": "PTO package variant 'a2a3sim' is not runnable in mode 'device'.",
                "mode": "device",
                "manifest_field": "target.variant",
                "manifest_value": "a2a3sim",
                "expected_platform": "a2a3",
            }
        ]


def test_load_rejects_invalid_mode(tmp_path):
    with _import_fresh_htp():
        from htp.backends.pto.emit import emit_package
        from htp.bindings.api import bind as bind_api

        package_dir = tmp_path / "package"
        package_dir.mkdir()
        emit_package(
            package_dir,
            program={
                "entry": "demo_kernel",
                "ops": ["compute_tile"],
            },
            variant="a2a3sim",
        )

        session = bind_api(package_dir).load(mode="banana")

        assert session.ok is False
        assert session.diagnostics == [
            {
                "code": "HTP.BINDINGS.INVALID_MODE",
                "detail": "Unsupported PTO binding mode: 'banana'.",
                "mode": "banana",
                "supported_modes": ["sim", "device"],
            }
        ]
