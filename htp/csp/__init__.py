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
) -> dict[str, Any]:
    return {
        "name": str(name),
        "task_id": str(task_id),
        "kernel": str(kernel),
        "args": [str(arg) for arg in args],
        "puts": [dict(item) for item in puts],
        "gets": [dict(item) for item in gets],
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
