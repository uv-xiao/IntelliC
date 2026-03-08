from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def workload(
    *, entry: str, tasks: Sequence[Mapping[str, Any]], channels: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    return {
        "entry": entry,
        "tasks": [dict(task) for task in tasks],
        "channels": [dict(channel) for channel in channels],
        "dependencies": [],
    }


def schedule(
    *,
    tile: Mapping[str, Any] | None = None,
    bind: Mapping[str, Any] | None = None,
    pipeline: Mapping[str, Any] | None = None,
    resources: Mapping[str, Any] | None = None,
    specialize: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "tile": dict(tile or {}),
        "bind": dict(bind or {}),
        "pipeline": dict(pipeline or {}),
        "resources": dict(resources or {}),
        "specialize": dict(specialize or {}),
    }


def program(
    *,
    entry: str,
    kernel: Mapping[str, Any],
    workload: Mapping[str, Any],
    schedule: Mapping[str, Any],
    target: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "entry": entry,
        "target": dict(target or {}),
        "kernel": dict(kernel),
        "wsp": {
            "workload": dict(workload),
            "schedule": dict(schedule),
        },
    }


__all__ = ["program", "schedule", "workload"]
