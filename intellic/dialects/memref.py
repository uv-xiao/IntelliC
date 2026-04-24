from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemRefType:
    element_type: object
    shape: tuple[int | None, ...]
    layout: object | None = None
    memory_space: object | None = None

    @property
    def rank(self) -> int:
        return len(self.shape)

    def __str__(self) -> str:
        dims = "x".join("?" if dim is None else str(dim) for dim in self.shape)
        return f"memref<{dims}x{self.element_type}>"
