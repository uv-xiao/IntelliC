from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .model import DistributionFacet, DistributionPlacement


def distribution_from_payload(
    payload: list[object] | tuple[object, ...] | None, *, rank: int
) -> DistributionFacet:
    if payload is None or len(payload) == 0:
        return DistributionFacet(tuple(DistributionPlacement(kind="replicate") for _ in range(rank)))
    dims: list[DistributionPlacement] = []
    for item in payload:
        if isinstance(item, str):
            dims.append(DistributionPlacement(kind=str(item)))
        elif isinstance(item, dict):
            dims.append(
                DistributionPlacement(
                    kind=str(item.get("kind", "replicate")),
                    axis=str(item["axis"]) if item.get("axis") is not None else None,
                )
            )
        else:
            raise TypeError(f"Unsupported distribution payload item: {item!r}")
    if len(dims) != rank:
        raise ValueError(f"Distribution rank mismatch: expected {rank} dims, got {len(dims)}")
    return DistributionFacet(tuple(dims))


def join_distribution_placements(
    lhs: DistributionPlacement, rhs: DistributionPlacement
) -> DistributionPlacement | None:
    if lhs.kind in {"replicate", "R"} and rhs.kind in {"replicate", "R"}:
        return DistributionPlacement(kind="replicate")
    if lhs.kind in {"replicate", "R"}:
        return rhs
    if rhs.kind in {"replicate", "R"}:
        return lhs
    if lhs.kind == rhs.kind == "shard" and lhs.axis == rhs.axis:
        return lhs
    return None


def join_distribution_facets(lhs: DistributionFacet, rhs: DistributionFacet) -> DistributionFacet | None:
    if len(lhs.dims) != len(rhs.dims):
        return None
    joined: list[DistributionPlacement] = []
    for left_dim, right_dim in zip(lhs.dims, rhs.dims, strict=True):
        dim = join_distribution_placements(left_dim, right_dim)
        if dim is None:
            return None
        joined.append(dim)
    return DistributionFacet(tuple(joined))


def distribution_matches(lhs: DistributionFacet, rhs: DistributionFacet) -> bool:
    return lhs == rhs


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
    "distribution_from_payload",
    "distribution_matches",
    "join_distribution_facets",
    "join_distribution_placements",
    "layout_to_payload",
]
