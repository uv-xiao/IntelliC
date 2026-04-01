from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .model import EffectsAspect, LayoutAspect, ScheduleAspect, TypesAspect


def _split_payload(payload: Mapping[str, Any], known_keys: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    core: dict[str, Any] = {}
    extras: dict[str, Any] = {}
    for key, value in payload.items():
        if key in known_keys:
            core[str(key)] = value
        elif key != "schema":
            extras[str(key)] = value
    return core, extras


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
    "effects_aspect_from_payload",
    "layout_aspect_from_payload",
    "schedule_aspect_from_payload",
    "types_aspect_from_payload",
]
