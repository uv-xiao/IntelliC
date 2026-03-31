from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class _AspectState(Mapping[str, Any]):
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
class TypesAspect(_AspectState):
    values: dict[str, Any] = field(default_factory=dict)
    buffers: dict[str, Any] = field(default_factory=dict)

    def _core_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "values": dict(self.values),
            "buffers": dict(self.buffers),
        }


@dataclass(frozen=True)
class LayoutAspect(_AspectState):
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
class EffectsAspect(_AspectState):
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
class ScheduleAspect(_AspectState):
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


def _split_payload(payload: Mapping[str, Any], known_keys: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    core: dict[str, Any] = {}
    extras: dict[str, Any] = {}
    for key, value in payload.items():
        if key in known_keys:
            core[str(key)] = value
        elif key != "schema":
            extras[str(key)] = value
    return core, extras


def _is_structurally_empty(payload: Mapping[str, Any]) -> bool:
    for key, value in payload.items():
        if key == "schema":
            continue
        if value not in ({}, [], (), 0, None):
            return False
    return True


def types_aspect_from_payload(payload: Mapping[str, Any]) -> TypesAspect:
    core, extras = _split_payload(payload, {"schema", "values", "buffers"})
    return TypesAspect(
        schema=str(core.get("schema", "htp.types.v1")),
        values=dict(core.get("values", {})),
        buffers=dict(core.get("buffers", {})),
        extras=extras,
    )


def layout_aspect_from_payload(payload: Mapping[str, Any]) -> LayoutAspect:
    core, extras = _split_payload(payload, {"schema", "memory_spaces", "threading", "tiling"})
    return LayoutAspect(
        schema=str(core.get("schema", "htp.layout.v1")),
        memory_spaces=dict(core.get("memory_spaces", {})),
        threading=dict(core.get("threading", {})),
        tiling=dict(core.get("tiling", {})),
        extras=extras,
    )


def effects_aspect_from_payload(payload: Mapping[str, Any]) -> EffectsAspect:
    core, extras = _split_payload(payload, {"schema", "reads", "writes", "barriers", "channels"})
    return EffectsAspect(
        schema=str(core.get("schema", "htp.effects.v1")),
        reads=dict(core.get("reads", {})),
        writes=dict(core.get("writes", {})),
        barriers=tuple(core.get("barriers", ())),
        channels=tuple(core.get("channels", ())),
        extras=extras,
    )


def schedule_aspect_from_payload(payload: Mapping[str, Any]) -> ScheduleAspect:
    core, extras = _split_payload(payload, {"schema", "ticks", "ordered_ops", "pipeline_depth"})
    return ScheduleAspect(
        schema=str(core.get("schema", "htp.schedule.v1")),
        ticks=tuple(core.get("ticks", ())),
        ordered_ops=tuple(core.get("ordered_ops", ())),
        pipeline_depth=int(core.get("pipeline_depth", 0)),
        extras=extras,
    )


__all__ = [
    "EffectsAspect",
    "LayoutAspect",
    "ScheduleAspect",
    "TypesAspect",
    "effects_aspect_from_payload",
    "layout_aspect_from_payload",
    "schedule_aspect_from_payload",
    "types_aspect_from_payload",
]
