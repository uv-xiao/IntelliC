from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .frontend_rules import FrontendBuildContext, FrontendRule
from .module import ProgramModule


@dataclass(frozen=True)
class FrontendSpec:
    frontend_id: str
    dialect_id: str
    surface_type: type[Any]
    build_program_module: Callable[[Any], ProgramModule] | None = None
    rule: FrontendRule | None = None

    def build(self, surface: Any) -> ProgramModule:
        if self.rule is not None:
            result = self.rule.apply(
                FrontendBuildContext(
                    frontend_id=self.frontend_id,
                    dialect_id=self.dialect_id,
                    surface=surface,
                )
            )
            if not isinstance(result.module, ProgramModule):
                raise TypeError(f"{self.frontend_id} rule must return a ProgramModule")
            return result.module
        if self.build_program_module is None:
            raise TypeError(f"{self.frontend_id} has no builder or rule")
        module = self.build_program_module(surface)
        if not isinstance(module, ProgramModule):
            raise TypeError(f"{self.frontend_id} must build a ProgramModule")
        return module


_FRONTEND_REGISTRY: dict[str, FrontendSpec] = {}


def register_frontend(spec: FrontendSpec, *, replace: bool = False) -> None:
    existing = _FRONTEND_REGISTRY.get(spec.frontend_id)
    if existing is not None and not replace:
        raise ValueError(f"Frontend {spec.frontend_id!r} is already registered")
    _FRONTEND_REGISTRY[spec.frontend_id] = spec


def frontend_registry_snapshot() -> dict[str, FrontendSpec]:
    return dict(_FRONTEND_REGISTRY)


def ensure_builtin_frontends() -> tuple[FrontendSpec, ...]:
    from htp.csp import CSPProgramSpec
    from htp.kernel import KernelSpec
    from htp.routine import ProgramSpec
    from htp.wsp import WSPProgramSpec

    builtin = (
        FrontendSpec(
            frontend_id="htp.kernel.KernelSpec",
            dialect_id="htp.kernel",
            surface_type=KernelSpec,
            build_program_module=lambda surface: surface.to_program_module(),
        ),
        FrontendSpec(
            frontend_id="htp.routine.ProgramSpec",
            dialect_id="htp.routine",
            surface_type=ProgramSpec,
            build_program_module=lambda surface: surface.to_program_module(),
        ),
        FrontendSpec(
            frontend_id="htp.wsp.WSPProgramSpec",
            dialect_id="htp.wsp",
            surface_type=WSPProgramSpec,
            build_program_module=lambda surface: surface.to_program_module(),
        ),
        FrontendSpec(
            frontend_id="htp.csp.CSPProgramSpec",
            dialect_id="htp.csp",
            surface_type=CSPProgramSpec,
            build_program_module=lambda surface: surface.to_program_module(),
        ),
    )
    for spec in builtin:
        if spec.frontend_id not in _FRONTEND_REGISTRY:
            register_frontend(spec)
    return tuple(_FRONTEND_REGISTRY[spec.frontend_id] for spec in builtin)


def resolve_frontend(surface: Any) -> FrontendSpec | None:
    ensure_builtin_frontends()
    for spec in _FRONTEND_REGISTRY.values():
        if isinstance(surface, spec.surface_type):
            return spec
    return None


__all__ = [
    "FrontendSpec",
    "ensure_builtin_frontends",
    "frontend_registry_snapshot",
    "register_frontend",
    "resolve_frontend",
]
