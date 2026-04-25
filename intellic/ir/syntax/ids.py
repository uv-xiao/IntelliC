from __future__ import annotations

from dataclasses import dataclass
from itertools import count


_next_id = count(1)


@dataclass(frozen=True, order=True)
class SyntaxId:
    """Stable process-local identity for syntax objects."""

    value: int

    @classmethod
    def fresh(cls) -> "SyntaxId":
        return cls(next(_next_id))

    def __str__(self) -> str:
        return f"sy{self.value}"
