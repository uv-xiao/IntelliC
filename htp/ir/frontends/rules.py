from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..program.module import ProgramModule
from .shared import FrontendWorkload, build_frontend_program_module


@dataclass(frozen=True)
class FrontendBuildContext:
    frontend_id: str
    dialect_id: str
    surface: Any
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FrontendRuleResult:
    module: ProgramModule
    evidence: dict[str, Any] = field(default_factory=dict)


class FrontendRule:
    def __init__(
        self,
        name: str,
        build: Callable[[FrontendBuildContext], FrontendRuleResult] | None = None,
    ) -> None:
        self.name = name
        self._build = build

    def apply(self, context: FrontendBuildContext) -> FrontendRuleResult:
        if self._build is None:  # pragma: no cover - subclass contract
            raise NotImplementedError(f"{type(self).__name__}.apply() must be implemented")
        return self._build(context)


class ProgramSurfaceRule(FrontendRule):
    """Shared rule substrate for public surfaces that lower through workload helpers."""

    def __init__(
        self,
        *,
        name: str,
        source_surface: str,
        active_dialects: tuple[str, ...],
        kernel_spec: Callable[[Any], Any],
        authored_program: Callable[[Any], dict[str, Any]],
        workload: Callable[[Any], FrontendWorkload],
    ) -> None:
        super().__init__(name)
        self.source_surface = source_surface
        self.active_dialects = active_dialects
        self.kernel_spec = kernel_spec
        self.authored_program = authored_program
        self.workload = workload

    def apply(self, context: FrontendBuildContext) -> FrontendRuleResult:
        surface = context.surface
        kernel_module = self.kernel_spec(surface).to_program_module()
        module = build_frontend_program_module(
            kernel_module=kernel_module,
            authored_program=self.authored_program(surface),
            workload=self.workload(surface),
            source_surface=self.source_surface,
            active_dialects=self.active_dialects,
        )
        return FrontendRuleResult(module=module)


__all__ = ["FrontendBuildContext", "FrontendRule", "FrontendRuleResult", "ProgramSurfaceRule"]
