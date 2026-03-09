from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from htp.compiler import parse_target
from htp.kernel import KernelSpec, KernelValue


def channel(name: str, *, dtype: str, capacity: int, protocol: str = "fifo") -> dict[str, Any]:
    return {
        "name": str(name),
        "dtype": str(dtype),
        "capacity": int(capacity),
        "protocol": str(protocol),
    }


def fifo(name: str, *, dtype: str, capacity: int) -> dict[str, Any]:
    return channel(name, dtype=dtype, capacity=capacity, protocol="fifo")


def put(channel: str, *, count: int = 1) -> dict[str, Any]:
    return {"kind": "put", "channel": str(channel), "count": int(count)}


def get(channel: str, *, count: int = 1) -> dict[str, Any]:
    return {"kind": "get", "channel": str(channel), "count": int(count)}


def process(
    name: str,
    *,
    task_id: str,
    kernel: KernelSpec | str,
    args: Sequence[str | KernelValue] = (),
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
        "kernel": kernel.name if isinstance(kernel, KernelSpec) else str(kernel),
        "args": [_ref(arg) for arg in args],
        "puts": derived_puts,
        "gets": derived_gets,
        **({"steps": normalized_steps} if normalized_steps else {}),
    }


def program(
    *,
    entry: str,
    kernel: Mapping[str, Any] | KernelSpec,
    channels: Sequence[Mapping[str, Any]],
    processes: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any] | str | None = None,
) -> dict[str, Any]:
    return {
        "entry": entry,
        "target": _normalize_target(target),
        "kernel": kernel.to_payload() if isinstance(kernel, KernelSpec) else dict(kernel),
        "csp": {
            "channels": [dict(item) for item in channels],
            "processes": [dict(item) for item in processes],
        },
    }


def _normalize_target(target: Mapping[str, Any] | str | None) -> dict[str, Any]:
    if target is None:
        return {}
    if isinstance(target, str):
        target_spec = parse_target(target)
        payload = {"backend": target_spec.backend}
        if target_spec.option is not None:
            payload["option"] = target_spec.option
        return payload
    return dict(target)


def _ref(value: str | KernelValue) -> str:
    if isinstance(value, KernelValue):
        return value.name
    return str(value)


__all__ = ["channel", "fifo", "get", "process", "program", "put"]
