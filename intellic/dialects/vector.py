from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VectorType:
    element_type: object
    shape: tuple[int | None, ...]

    def __post_init__(self) -> None:
        if any(dim is None for dim in self.shape):
            raise ValueError("vector shape must be static")
        if any(dim <= 0 for dim in self.shape if dim is not None):
            raise ValueError("vector shape dimensions must be positive")

    def __str__(self) -> str:
        dims = "x".join(str(dim) for dim in self.shape)
        return f"vector<{dims}x{self.element_type}>"
