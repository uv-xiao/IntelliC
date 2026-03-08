from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


@dataclass(frozen=True)
class DistributionPlacement:
    kind: str
    axis: str | None = None


@dataclass(frozen=True)
class DistributionFacet:
    dims: tuple[DistributionPlacement, ...]


@dataclass(frozen=True)
class MemoryFacet:
    space: str
    layout: str
    order: tuple[int, ...]


@dataclass(frozen=True)
class HardwareFacet:
    scope: str
    vector_width: int


@dataclass(frozen=True)
class LayoutFacetProduct:
    distribution: DistributionFacet
    memory: MemoryFacet
    hardware: HardwareFacet


def layout_to_payload(value: Any) -> Any:
    if is_dataclass(value):
        return {
            str(key): layout_to_payload(item)
            for key, item in asdict(value).items()
            if item is not None and item != [None] and item != (None,)
        }
    if isinstance(value, dict):
        return {str(key): layout_to_payload(item) for key, item in value.items() if item is not None}
    if isinstance(value, (list, tuple)):
        return [layout_to_payload(item) for item in value if item is not None]
    return value


__all__ = [
    "DistributionFacet",
    "DistributionPlacement",
    "HardwareFacet",
    "LayoutFacetProduct",
    "MemoryFacet",
    "layout_to_payload",
]
