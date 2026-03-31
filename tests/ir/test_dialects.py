from __future__ import annotations

import pytest

from htp.ir.dialects import (
    DialectSpec,
    dialect_registry_snapshot,
    ensure_builtin_dialects,
    normalize_active_dialects,
    register_dialect,
    resolve_dialects,
)


def test_builtin_dialects_are_registered_and_resolvable():
    builtin = ensure_builtin_dialects()
    snapshot = dialect_registry_snapshot()

    assert [spec.dialect_id for spec in builtin] == [
        "htp.core",
        "htp.kernel",
        "htp.routine",
        "htp.wsp",
        "htp.csp",
    ]
    assert snapshot["htp.kernel"].dependencies == ("htp.core",)
    assert [spec.dialect_id for spec in resolve_dialects(("htp.core", "htp.kernel"))] == [
        "htp.core",
        "htp.kernel",
    ]
    assert normalize_active_dialects("htp.core", "htp.wsp") == ("htp.core", "htp.wsp")


def test_register_dialect_rejects_duplicate_without_replace():
    spec = DialectSpec(
        dialect_id="htp.test.analysis",
        version="v1",
        kind="test",
        exports=("AnalysisRecord",),
    )
    register_dialect(spec, replace=True)

    with pytest.raises(ValueError, match="already registered"):
        register_dialect(spec)
