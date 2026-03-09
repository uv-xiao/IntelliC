"""Public WSP authoring helpers.

This module keeps the explicit payload surface for low-level tests, while
making the preferred public surface traced Python via ``@wsp.program(...)`` and
``wsp.task(...)``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from inspect import signature
from typing import Any

from htp.compiler import parse_target
from htp.kernel import KernelArgSpec, KernelSpec, KernelValue
from htp.routine import DependencySpec


@dataclass(frozen=True)
class WSPTaskSpec:
    """A single workload task in the public WSP surface."""

    task_id: str
    kernel: str
    args: tuple[str, ...]
    kind: str = "kernel_call"

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "kernel": self.kernel,
            "args": list(self.args),
        }


@dataclass(frozen=True)
class WSPTaskHandle:
    """Dependency handle returned by traced ``wsp.task(...)`` calls."""

    task_id: str


@dataclass(frozen=True)
class WSPProgramSpec:
    """High-level WSP authoring surface accepted by ``compile_program``."""

    entry: str
    kernel: KernelSpec
    tasks: tuple[WSPTaskSpec, ...]
    dependencies: tuple[DependencySpec, ...]
    schedule_directives: dict[str, Any]
    target: dict[str, Any]

    def to_program(self) -> dict[str, Any]:
        return {
            "entry": self.entry,
            "target": dict(self.target),
            "kernel": self.kernel.to_payload(),
            "wsp": {
                "workload": {
                    "entry": self.entry,
                    "tasks": [task.to_payload() for task in self.tasks],
                    "channels": [],
                    "dependencies": [dependency.to_payload() for dependency in self.dependencies],
                },
                "schedule": dict(self.schedule_directives),
            },
        }


@dataclass
class _WSPTrace:
    tasks: list[WSPTaskSpec]
    dependencies: list[DependencySpec]
    seen_kernel: KernelSpec | None
    task_counts: dict[str, int]


_WSP_TRACE: ContextVar[_WSPTrace | None] = ContextVar("htp_wsp_trace", default=None)


def task(
    kernel: KernelSpec | str,
    *args: str | KernelValue,
    task_id: str | None = None,
    kind: str = "kernel_call",
    after: WSPTaskHandle | None = None,
) -> dict[str, Any] | WSPTaskHandle:
    """Create a WSP task.

    Outside a traced ``@wsp.program`` body this returns an explicit payload dict.
    Inside a traced body it records the task and returns a handle for ``after=``.
    """

    kernel_name = kernel.name if isinstance(kernel, KernelSpec) else str(kernel)
    trace = _WSP_TRACE.get()
    resolved_task_id = task_id
    if trace is not None:
        if trace.seen_kernel is None:
            if not isinstance(kernel, KernelSpec):
                raise TypeError("Traced WSP task(...) requires a KernelSpec, not only a kernel name.")
            trace.seen_kernel = kernel
        elif trace.seen_kernel.name != kernel_name:
            raise ValueError("The current WSP public surface supports exactly one kernel per program.")
        if resolved_task_id is None:
            resolved_task_id = _auto_task_id(trace, kernel_name)
        trace.tasks.append(
            WSPTaskSpec(
                task_id=resolved_task_id,
                kernel=kernel_name,
                args=tuple(_ref(arg) for arg in args),
                kind=kind,
            )
        )
        if after is not None:
            trace.dependencies.append(DependencySpec(src=after.task_id, dst=resolved_task_id))
        return WSPTaskHandle(task_id=resolved_task_id)
    if resolved_task_id is None:
        resolved_task_id = f"{kernel_name}_0"
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
    function: Callable[..., Any] | None = None,
    *,
    entry: str | None = None,
    kernel: Mapping[str, Any] | KernelSpec | None = None,
    workload: Mapping[str, Any] | None = None,
    tasks: Sequence[Mapping[str, Any]] | None = None,
    schedule: Mapping[str, Any] | None = None,
    target: Mapping[str, Any] | str | None = None,
    tile: Mapping[str, Any] | None = None,
    bind: Mapping[str, Any] | None = None,
    pipeline: Mapping[str, Any] | None = None,
    resources: Mapping[str, Any] | None = None,
    specialize: Mapping[str, Any] | None = None,
) -> WSPProgramSpec | dict[str, Any] | Callable[[Callable[..., Any]], WSPProgramSpec]:
    """Create a WSP program from explicit payloads or traced Python."""

    traced_schedule = _coalesce_schedule(
        explicit=schedule,
        tile_directives=tile,
        bind_directives=bind,
        pipeline_directives=pipeline,
        resource_directives=resources,
        specialize_directives=specialize,
    )
    if function is None and kernel is None and workload is None and tasks is None:
        return lambda traced_function: _trace_program(
            traced_function,
            target=target,
            schedule_directives=traced_schedule,
        )
    if function is not None and callable(function) and kernel is None and workload is None and tasks is None:
        return _trace_program(function, target=target, schedule_directives=traced_schedule)
    if entry is None or kernel is None:
        raise TypeError("wsp.program(...) expects either decorator usage or explicit entry= and kernel=")
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
            "schedule": traced_schedule,
        },
    }


def _trace_program(
    function: Callable[..., Any],
    *,
    target: Mapping[str, Any] | str | None,
    schedule_directives: Mapping[str, Any],
) -> WSPProgramSpec:
    values = _annotated_values(function)
    token = _WSP_TRACE.set(_WSPTrace(tasks=[], dependencies=[], seen_kernel=None, task_counts={}))
    try:
        function(*values)
        trace = _WSP_TRACE.get()
    finally:
        _WSP_TRACE.reset(token)
    if trace is None or trace.seen_kernel is None:
        raise ValueError(f"Traced WSP program {function.__name__!r} did not record any wsp.task(...) sites")
    return WSPProgramSpec(
        entry=function.__name__,
        kernel=trace.seen_kernel,
        tasks=tuple(trace.tasks),
        dependencies=tuple(trace.dependencies),
        schedule_directives=dict(schedule_directives),
        target=_normalize_target(target),
    )


def _annotated_values(function: Callable[..., Any]) -> list[KernelValue]:
    values: list[KernelValue] = []
    for parameter_name, parameter in signature(function).parameters.items():
        annotation = _resolve_annotation(parameter.annotation, function=function)
        if not isinstance(annotation, KernelArgSpec):
            raise TypeError(
                f"Traced WSP parameter {parameter_name!r} must use htp.kernel.buffer(...) or htp.kernel.scalar(...) annotation"
            )
        values.append(
            KernelValue(
                parameter_name,
                dtype=annotation.dtype,
                shape=annotation.shape,
                kind=annotation.kind,
                role=annotation.role,
            )
        )
    return values


def _coalesce_schedule(
    *,
    explicit: Mapping[str, Any] | None,
    tile_directives: Mapping[str, Any] | None,
    bind_directives: Mapping[str, Any] | None,
    pipeline_directives: Mapping[str, Any] | None,
    resource_directives: Mapping[str, Any] | None,
    specialize_directives: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if explicit is not None:
        return dict(explicit)
    return schedule(
        tile=tile_directives,
        bind=bind_directives,
        pipeline=pipeline_directives,
        resources=resource_directives,
        specialize=specialize_directives,
    )


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


def _resolve_annotation(annotation: Any, *, function: Callable[..., Any]) -> Any:
    if isinstance(annotation, str):
        return eval(annotation, function.__globals__, function.__globals__)
    return annotation


def _ref(value: str | KernelValue) -> str:
    if isinstance(value, KernelValue):
        return value.name
    return str(value)


def _auto_task_id(trace: _WSPTrace, kernel_name: str) -> str:
    index = trace.task_counts.get(kernel_name, 0)
    trace.task_counts[kernel_name] = index + 1
    return f"{kernel_name}_{index}"


__all__ = [
    "WSPProgramSpec",
    "WSPTaskHandle",
    "WSPTaskSpec",
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
