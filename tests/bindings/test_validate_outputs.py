from __future__ import annotations

from htp.bindings import bind
from tests.conftest import copy_golden_fixture


def test_binding_validate_checks_manifest_outputs(tmp_path):
    package_dir = copy_golden_fixture("pto_demo", tmp_path)
    missing_path = package_dir / "codegen/pto/kernel_config.py"
    missing_path.unlink()

    result = bind(package_dir).validate()

    assert result.ok is False
    assert "codegen/pto/kernel_config.py" in result.missing_files
    assert {
        "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
        "detail": "Missing required PTO artifact path: codegen/pto/kernel_config.py",
    } in result.diagnostics
