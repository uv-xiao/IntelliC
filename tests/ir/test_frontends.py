from __future__ import annotations

from htp.ir.frontends import ensure_builtin_frontends, frontend_registry_snapshot, resolve_frontend
from htp.kernel import KernelSpec


def test_builtin_frontends_are_registered_and_resolvable() -> None:
    builtin = ensure_builtin_frontends()
    snapshot = frontend_registry_snapshot()

    assert [spec.frontend_id for spec in builtin] == [
        "htp.kernel.KernelSpec",
        "htp.routine.ProgramSpec",
        "htp.wsp.WSPProgramSpec",
        "htp.csp.CSPProgramSpec",
    ]
    assert snapshot["htp.kernel.KernelSpec"].dialect_id == "htp.kernel"
    assert resolve_frontend(KernelSpec(name="affine", args=(), ops=())) == snapshot["htp.kernel.KernelSpec"]


def test_resolve_frontend_returns_none_for_unregistered_surface() -> None:
    class UnknownSurface:
        pass

    assert resolve_frontend(UnknownSurface()) is None


def test_builtin_frontend_builds_program_module() -> None:
    spec = ensure_builtin_frontends()[0]
    module = spec.build_program_module(KernelSpec(name="affine", args=(), ops=()))

    assert module.items.kernel_ir.entry == "affine"
    assert module.meta["source_surface"] == "htp.kernel.KernelSpec"
    assert module.meta["active_dialects"] == ["htp.core", "htp.kernel"]
