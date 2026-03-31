from __future__ import annotations

import pytest

from htp.ir.dialects import (
    DialectActivation,
    DialectExports,
    DialectSpec,
    activate_dialects,
    dialect_activation_payload,
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
    assert snapshot["htp.core"].exports.interpreters == ("snapshot",)
    assert [spec.dialect_id for spec in resolve_dialects(("htp.core", "htp.kernel"))] == [
        "htp.core",
        "htp.kernel",
    ]
    assert normalize_active_dialects("htp.wsp") == ("htp.core", "htp.kernel", "htp.wsp")


def test_activate_dialects_records_requested_and_dependency_closed_resolution():
    activation = activate_dialects("htp.wsp")

    assert isinstance(activation, DialectActivation)
    assert activation.requested == ("htp.wsp",)
    assert activation.dialect_ids() == ("htp.core", "htp.kernel", "htp.wsp")
    assert dialect_activation_payload("htp.wsp") == {
        "active_dialects": ["htp.core", "htp.kernel", "htp.wsp"],
        "dialect_activation": activation.to_payload(),
    }


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


def test_resolve_dialects_rejects_unknown_dependency() -> None:
    register_dialect(
        DialectSpec(
            dialect_id="htp.test.missing_dep",
            version="v1",
            kind="test",
            dependencies=("htp.test.does_not_exist",),
            exports=DialectExports(frontends=("missing",)),
        ),
        replace=True,
    )

    with pytest.raises(KeyError, match="htp.test.does_not_exist"):
        resolve_dialects(("htp.test.missing_dep",))
