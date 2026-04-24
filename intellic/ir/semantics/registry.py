from __future__ import annotations

from .level import SemanticLevelKey
from .semantic_def import SemanticDef


class SemanticRegistry:
    def __init__(self) -> None:
        self._defs: dict[tuple[object, SemanticLevelKey], SemanticDef] = {}

    def register(self, semantic_def: SemanticDef) -> None:
        key = (semantic_def.owner, semantic_def.level)
        if key in self._defs:
            raise ValueError(f"duplicate semantic definition for {semantic_def.owner}")
        self._defs[key] = semantic_def

    def resolve(self, owner: object, level: SemanticLevelKey) -> SemanticDef:
        try:
            return self._defs[(owner, level)]
        except KeyError as exc:
            raise KeyError(f"missing semantic definition for {owner}") from exc
