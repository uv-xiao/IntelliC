from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Type:
    """Immutable IR type."""

    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("type name must be non-empty")

    def __str__(self) -> str:
        return self.name


i1 = Type("i1")
i32 = Type("i32")
index = Type("index")
