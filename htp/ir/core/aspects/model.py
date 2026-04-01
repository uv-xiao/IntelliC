from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AspectState(Mapping[str, Any]):
    """Typed base class for long-lived ProgramModule semantic aspects."""

    schema: str
    extras: dict[str, Any] = field(default_factory=dict)

    def _core_payload(self) -> dict[str, Any]:
        return {"schema": self.schema}

    def to_payload(self) -> dict[str, Any]:
        payload = self._core_payload()
        payload.update(self.extras)
        if _is_structurally_empty(payload):
            return {}
        return payload

    def __getitem__(self, key: str) -> Any:
        return self.to_payload()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_payload())

    def __len__(self) -> int:
        return len(self.to_payload())


@dataclass(frozen=True)
class TypesAspect(AspectState):
    values: dict[str, Any] = field(default_factory=dict)
    buffers: dict[str, Any] = field(default_factory=dict)

    def _core_payload(self) -> dict[str, Any]:
        return {"schema": self.schema, "values": dict(self.values), "buffers": dict(self.buffers)}


@dataclass(frozen=True)
class LayoutAspect(AspectState):
    memory_spaces: dict[str, Any] = field(default_factory=dict)
    threading: dict[str, Any] = field(default_factory=dict)
    tiling: dict[str, Any] = field(default_factory=dict)

    def _core_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "memory_spaces": dict(self.memory_spaces),
            "threading": dict(self.threading),
            "tiling": dict(self.tiling),
        }


@dataclass(frozen=True)
class EffectsAspect(AspectState):
    reads: dict[str, Any] = field(default_factory=dict)
    writes: dict[str, Any] = field(default_factory=dict)
    barriers: tuple[Any, ...] = ()
    channels: tuple[Any, ...] = ()

    def _core_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "reads": dict(self.reads),
            "writes": dict(self.writes),
            "barriers": list(self.barriers),
            "channels": list(self.channels),
        }


@dataclass(frozen=True)
class ScheduleAspect(AspectState):
    ticks: tuple[Any, ...] = ()
    ordered_ops: tuple[Any, ...] = ()
    pipeline_depth: int = 0

    def _core_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "ticks": list(self.ticks),
            "ordered_ops": list(self.ordered_ops),
            "pipeline_depth": self.pipeline_depth,
        }


def _is_structurally_empty(payload: Mapping[str, Any]) -> bool:
    for key, value in payload.items():
        if key == "schema":
            continue
        if value not in ({}, [], (), 0, None):
            return False
    return True


__all__ = ["AspectState", "EffectsAspect", "LayoutAspect", "ScheduleAspect", "TypesAspect"]
