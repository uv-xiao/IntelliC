from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Attribute:
    """Immutable compile-time operation data."""

    name: str
    value: Any = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("attribute name must be non-empty")
