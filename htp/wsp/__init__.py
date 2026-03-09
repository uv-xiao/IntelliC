"""WSP authoring helpers and builder surface.

This module keeps the original payload-builder helpers for low-level contract
tests, but the primary public surface is now the decorator/builder path:

    @wsp.program(target="nvgpu-ampere", kernel=my_kernel)
    def my_workload(w):
        (
            w.launch(my_kernel, "A", "B", "C", "M", "N", "K", task_id="main")
            .tile(block=(128, 128, 32))
            .bind(grid="block", lane="warp")
            .pipeline(depth=3, buffering="double")
            .resources(num_warps=8)
            .specialize(operator="matmul")
        )

That keeps WSP authoring in normal Python while preserving the existing
`to_program()` contract shape.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from inspect import signature
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
        "tasks": [dict(item) for item in tasks],
        "channels": [dict(item) for item in channels],
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


def specialize(*, operator: str, **attrs: Any) -> dict[str, Any]:
    return {"operator": operator, **dict(attrs)}


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


@dataclass(frozen=True)
class WSPProgramSpec:
    """Frozen WSP program surface that compiles through `to_program()`."""

    entry: str
    target: dict[str, Any]
    kernel: dict[str, Any]
    workload: dict[str, Any]
    schedule: dict[str, Any]

    def to_program(self) -> dict[str, Any]:
        return {
            "entry": self.entry,
            "target": dict(self.target),
            "kernel": dict(self.kernel),
            "wsp": {
                "workload": {
                    "entry": str(self.workload["entry"]),
                    "tasks": [dict(item) for item in self.workload.get("tasks", ())],
                    "channels": [dict(item) for item in self.workload.get("channels", ())],
                    "dependencies": [dict(item) for item in self.workload.get("dependencies", ())],
                },
                "schedule": {
                    key: dict(value) if isinstance(value, Mapping) else value
                    for key, value in self.schedule.items()
                },
            },
        }


@dataclass
class WSPBuilder:
    """Mutable builder used by `@wsp.program(...)` decorator mode."""

    entry: str
    kernel_spec: KernelSpec
    target: dict[str, Any]
    tasks: list[dict[str, Any]] = field(default_factory=list)
    channels: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    schedule_state: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "tile": {},
            "bind": {},
            "pipeline": {},
            "resources": {},
            "specialize": {},
        }
    )

    def launch(
        self,
        kernel: KernelSpec | str,
        *args: str | KernelValue,
        task_id: str | None = None,
        kind: str = "kernel_call",
    ) -> WSPBuilder:
        self.tasks.append(task(kernel, *args, task_id=task_id, kind=kind))
        return self

    def task(
        self,
        kernel: KernelSpec | str,
        *args: str | KernelValue,
        task_id: str | None = None,
        kind: str = "kernel_call",
    ) -> WSPBuilder:
        return self.launch(kernel, *args, task_id=task_id, kind=kind)

    def tile(self, *, block: tuple[int, int, int] | list[int]) -> WSPBuilder:
        self.schedule_state["tile"] = tile(block=block)
        return self

    def bind(self, *, grid: str | None = None, lane: str | None = None) -> WSPBuilder:
        self.schedule_state["bind"] = bind(grid=grid, lane=lane)
        return self

    def pipeline(self, *, depth: int, buffering: str = "double") -> WSPBuilder:
        self.schedule_state["pipeline"] = pipeline(depth=depth, buffering=buffering)
        return self

    def resources(self, *, num_warps: int) -> WSPBuilder:
        self.schedule_state["resources"] = resources(num_warps=num_warps)
        return self

    def specialize(self, *, operator: str, **attrs: Any) -> WSPBuilder:
        self.schedule_state["specialize"] = specialize(operator=operator, **attrs)
        return self

    def to_program(self) -> dict[str, Any]:
        return WSPProgramSpec(
            entry=self.entry,
            target=self.target,
            kernel=self.kernel_spec.to_payload(),
            workload=workload(entry=self.entry, tasks=self.tasks, channels=self.channels),
            schedule=self.schedule_state,
        ).to_program()


def program(
    *,
    entry: str | None = None,
    kernel: Mapping[str, Any] | KernelSpec,
    workload: Mapping[str, Any] | None = None,
    tasks: Sequence[Mapping[str, Any]] | None = None,
    schedule: Mapping[str, Any] | None = None,
    target: Mapping[str, Any] | str | None = None,
) -> dict[str, Any] | Callable[[Callable[..., Any]], WSPProgramSpec]:
    kernel_payload = kernel.to_payload() if isinstance(kernel, KernelSpec) else dict(kernel)

    if (
        workload is not None
        or tasks is not None
        or schedule is not None
        or entry is not None
        and isinstance(kernel, Mapping)
    ):
        if entry is None:
            raise TypeError(
                "wsp.program(..., kernel=<mapping>, ...) requires entry= when used as a payload builder."
            )
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
                "schedule": dict(schedule or {}),
            },
        }

    if not isinstance(kernel, KernelSpec):
        raise TypeError("Decorator-form wsp.program(...) requires kernel=<KernelSpec>.")

    def decorator(function: Callable[..., Any]) -> WSPProgramSpec:
        builder = WSPBuilder(
            entry=entry or function.__name__,
            kernel_spec=kernel,
            target=_normalize_target(target),
        )
        if len(signature(function).parameters) == 0:
            function()
        else:
            function(builder)
        return WSPProgramSpec(
            entry=builder.entry,
            target=builder.target,
            kernel=builder.kernel_spec.to_payload(),
            workload={
                "entry": builder.entry,
                "tasks": [dict(item) for item in builder.tasks],
                "channels": [dict(item) for item in builder.channels],
                "dependencies": [dict(item) for item in builder.dependencies],
            },
            schedule=builder.schedule_state,
        )

    return decorator


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
    "WSPBuilder",
    "WSPProgramSpec",
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
