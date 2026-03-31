from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .module import ProgramModule


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


@dataclass(frozen=True)
class FrontendRule:
    name: str
    build: Callable[[FrontendBuildContext], FrontendRuleResult]

    def apply(self, context: FrontendBuildContext) -> FrontendRuleResult:
        return self.build(context)


__all__ = ["FrontendBuildContext", "FrontendRule", "FrontendRuleResult"]
