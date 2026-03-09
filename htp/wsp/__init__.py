from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from htp.compiler import parse_target
from htp.kernel import KernelSpec, KernelValue


def task(
    kernel: KernelSpec | str,
    *args: str | KernelValue,
    task_id: str | None = None,
    kind: str = "kernel_call",
) -> dict[str, Any]:
    kernel_name = kernel.name if isinstance(kernel, KernelSpec) else str(kernel)
    resolved_task_id = task_id or f"{kernel_name}_0"
    return {
        "task_id": resolved_task_id,
        "kind": kind,
        "kernel": kernel_name,
        "args": [_ref(arg) for arg in args],
    }


def workload(
    *, entry: str, tasks: Sequence[Mapping[str, Any]], channels: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    return {
        "entry": entry,
        "tasks": [dict(task) for task in tasks],
        "channels": [dict(channel) for channel in channels],
        "dependencies": [],
    }


def tile(*, block: tuple[int, int, int] | list[int]) -> dict[str, Any]:
    return {"block": list(block)}


def bind(*, grid: str | None = None, lane: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if grid is not None:
        payload["grid"] = grid
    if lane is not None:
        payload["lane"] = lane
    return payload


def pipeline(*, depth: int, buffering: str = "double") -> dict[str, Any]:
    return {"depth": depth, "buffering": buffering}


def resources(*, num_warps: int) -> dict[str, Any]:
    return {"num_warps": num_warps}


def specialize(*, operator: str) -> dict[str, Any]:
    return {"operator": operator}


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
    kernel: Mapping[str, Any] | KernelSpec,
    workload: Mapping[str, Any] | None = None,
    tasks: Sequence[Mapping[str, Any]] | None = None,
    schedule: Mapping[str, Any],
    target: Mapping[str, Any] | str | None = None,
) -> dict[str, Any]:
    kernel_payload = kernel.to_payload() if isinstance(kernel, KernelSpec) else dict(kernel)
    workload_payload = (
        dict(workload)
        if workload is not None
        else {
            "entry": entry,
            "tasks": [dict(item) for item in (tasks or ())],
            "channels": [],
            "dependencies": [],
        }
    )
    return {
        "entry": entry,
        "target": _normalize_target(target),
        "kernel": kernel_payload,
        "wsp": {
            "workload": workload_payload,
            "schedule": dict(schedule),
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


__all__ = [
    "bind",
    "pipeline",
    "program",
    "resources",
    "schedule",
    "specialize",
    "task",
    "tile",
    "workload",
]
