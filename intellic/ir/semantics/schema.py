from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationSchema:
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("relation schema name must be non-empty")
