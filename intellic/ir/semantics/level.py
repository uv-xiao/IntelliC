from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticLevelKey:
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("semantic level name must be non-empty")
