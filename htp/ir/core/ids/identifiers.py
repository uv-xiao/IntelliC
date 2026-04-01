from __future__ import annotations

import re


def node_id(def_id: str, kind: str, ordinal: int) -> str:
    return f"{def_id}:{kind}:{ordinal}"


def entity_id(def_id: str, ordinal: int) -> str:
    return f"{def_id}:E{ordinal}"


def scope_id(def_id: str, ordinal: int) -> str:
    return f"{def_id}:S{ordinal}"


def binding_id(scope: str, ordinal: int) -> str:
    return f"{scope}:B{ordinal}"


def _natural_sort_key(value: str) -> tuple[tuple[int, object], ...]:
    return tuple(
        (0, int(segment)) if segment.isdigit() else (1, segment)
        for segment in re.split(r"(\d+)", value)
        if segment
    )


__all__ = ["_natural_sort_key", "binding_id", "entity_id", "node_id", "scope_id"]
