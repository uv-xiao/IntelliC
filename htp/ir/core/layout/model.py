from __future__ import annotations

from dataclasses import dataclass


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


__all__ = [
    "DistributionFacet",
    "DistributionPlacement",
    "HardwareFacet",
    "LayoutFacetProduct",
    "MemoryFacet",
]
