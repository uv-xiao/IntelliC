from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .level import SemanticLevelKey


@dataclass(frozen=True)
class SemanticDef:
    owner: object
    level: SemanticLevelKey
    apply: Callable
