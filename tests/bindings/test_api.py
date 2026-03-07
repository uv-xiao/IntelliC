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
        assert report.ok is True
        assert report.backend == "pto"
        assert report.variant == "a2a3sim"
        assert report.missing_files == []


def test_load_returns_normalized_load_result_shape(tmp_path):
    with _import_fresh_htp():
        from htp.bindings.api import bind as bind_api

        package_dir = tmp_path / "package"
        package_dir.mkdir()
        _write_manifest(package_dir)

        session = bind_api(package_dir).load(mode="sim")

        assert session.__class__.__name__ == "LoadResult"
        assert session.ok is True
        assert session.mode == "sim"
        assert session.backend == "pto"
        assert session.variant == "a2a3sim"
        assert session.diagnostics == []
