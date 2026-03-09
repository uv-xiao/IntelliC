from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def channel(name: str, *, dtype: str, capacity: int, protocol: str = "fifo") -> dict[str, Any]:
    return {
        "name": str(name),
        "dtype": str(dtype),
        "capacity": int(capacity),
        "protocol": str(protocol),
    }


def process(
    name: str,
    *,
    task_id: str,
    kernel: str,
    args: Sequence[str] = (),
    puts: Sequence[Mapping[str, Any]] = (),
    gets: Sequence[Mapping[str, Any]] = (),
    steps: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    normalized_steps = [dict(item) for item in steps]
    if normalized_steps:
        derived_puts = [dict(item) for item in normalized_steps if str(item.get("kind")) == "put"]
        derived_gets = [dict(item) for item in normalized_steps if str(item.get("kind")) == "get"]
    else:
        derived_puts = [dict(item) for item in puts]
        derived_gets = [dict(item) for item in gets]
    return {
        "name": str(name),
        "task_id": str(task_id),
        "kernel": str(kernel),
        "args": [str(arg) for arg in args],
        "puts": derived_puts,
        "gets": derived_gets,
        **({"steps": normalized_steps} if normalized_steps else {}),
    }


def program(
    *,
    entry: str,
    kernel: Mapping[str, Any],
    channels: Sequence[Mapping[str, Any]],
    processes: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "entry": entry,
        "target": dict(target or {}),
        "kernel": dict(kernel),
        "csp": {
            "channels": [dict(item) for item in channels],
            "processes": [dict(item) for item in processes],
        },
    }


__all__ = ["channel", "process", "program"]
