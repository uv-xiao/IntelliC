"""Public routine/workload authoring helpers for human-first HTP programs."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from inspect import signature
from typing import Any, Callable

from htp.compiler import parse_target
from htp.kernel import KernelArgSpec, KernelSpec, KernelValue


@dataclass(frozen=True)
class KernelCallSpec:
    """A readable task-level call edge in a routine/workload program."""

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
class DependencySpec:
    """A directed dependency edge between workload tasks."""

    src: str
    dst: str

    def to_payload(self) -> dict[str, str]:
        return {"src": self.src, "dst": self.dst}


@dataclass(frozen=True)
class ChannelSpec:
    """A typed public workload channel surface."""

    name: str
    dtype: str
    capacity: int
    protocol: str = "fifo"

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "capacity": self.capacity,
            "protocol": self.protocol,
        }


@dataclass(frozen=True)
class TaskHandle:
    """A lightweight dependency handle returned by traced routine calls."""

    task_id: str


@dataclass(frozen=True)
class ProgramSpec:
    """High-level public surface for ``compile_program`` inputs."""

    entry: str
    kernel: KernelSpec
    tasks: tuple[KernelCallSpec, ...]
    dependencies: tuple[DependencySpec, ...] = ()
    channels: tuple[ChannelSpec, ...] = ()
    target: dict[str, Any] | None = None

    def to_program(self) -> dict[str, Any]:
        return {
            "entry": self.entry,
            "target": dict(self.target or {}),
            "kernel": self.kernel.to_payload(),
            "workload": {
                "entry": self.entry,
                "tasks": [task.to_payload() for task in self.tasks],
                "channels": [channel.to_payload() for channel in self.channels],
                "dependencies": [dependency.to_payload() for dependency in self.dependencies],
            },
        }


@dataclass
class _ProgramTrace:
    tasks: list[KernelCallSpec]
    dependencies: list[DependencySpec]
    channels: list[ChannelSpec]
    seen_kernel: KernelSpec | None = None


_PROGRAM_TRACE: ContextVar[_ProgramTrace | None] = ContextVar("htp_program_trace", default=None)


def kernel_call(task_id: str, kernel: str, *args: str) -> KernelCallSpec:
    return KernelCallSpec(task_id=task_id, kernel=kernel, args=tuple(args))


def dependency(src: str, dst: str) -> DependencySpec:
    return DependencySpec(src=src, dst=dst)


def channel(name: str, *, dtype: str, capacity: int, protocol: str = "fifo") -> ChannelSpec:
    spec = ChannelSpec(name=name, dtype=dtype, capacity=capacity, protocol=protocol)
    trace = _PROGRAM_TRACE.get()
    if trace is not None:
        trace.channels.append(spec)
    return spec


def fifo_channel(name: str, *, dtype: str, capacity: int) -> ChannelSpec:
    return channel(name, dtype=dtype, capacity=capacity, protocol="fifo")


def call(
    kernel_spec: KernelSpec,
    *args: str | KernelValue,
    task: str,
    after: TaskHandle | None = None,
) -> TaskHandle:
    trace = _PROGRAM_TRACE.get()
    if trace is None:
        raise RuntimeError("htp.routine.call(...) must be used inside a traced @program function")
    if trace.seen_kernel is None:
        trace.seen_kernel = kernel_spec
    elif trace.seen_kernel.name != kernel_spec.name:
        raise ValueError("The current public routine surface supports exactly one kernel per program")
    task_spec = KernelCallSpec(task_id=task, kernel=kernel_spec.name, args=tuple(_ref(arg) for arg in args))
    trace.tasks.append(task_spec)
    if after is not None:
        trace.dependencies.append(DependencySpec(src=after.task_id, dst=task))
    return TaskHandle(task_id=task)


def program(
    function: Callable[..., Any] | None = None,
    *,
    entry: str | None = None,
    kernel: KernelSpec | None = None,
    tasks: list[KernelCallSpec] | tuple[KernelCallSpec, ...] | None = None,
    dependencies: list[DependencySpec] | tuple[DependencySpec, ...] = (),
    channels: list[ChannelSpec] | tuple[ChannelSpec, ...] = (),
    target: dict[str, Any] | str | None = None,
) -> ProgramSpec | Callable[[Callable[..., Any]], ProgramSpec]:
    if function is None and kernel is None and tasks is None:
        return lambda traced_function: _trace_program(traced_function, target=target)
    if function is not None and callable(function) and kernel is None and tasks is None:
        return _trace_program(function, target=target)
    if entry is None or kernel is None or tasks is None:
        raise TypeError("program(...) expects either decorator usage or explicit entry=, kernel=, and tasks=")
    return ProgramSpec(
        entry=entry,
        kernel=kernel,
        tasks=tuple(tasks),
        dependencies=tuple(dependencies),
        channels=tuple(channels),
        target=_normalize_target(target),
    )


def _trace_program(function: Callable[..., Any], *, target: dict[str, Any] | str | None) -> ProgramSpec:
    parameters = signature(function).parameters
    values: list[KernelValue] = []
    for parameter_name, parameter in parameters.items():
        annotation = _resolve_annotation(parameter.annotation, function=function)
        if not isinstance(annotation, KernelArgSpec):
            raise TypeError(
                f"Traced program parameter {parameter_name!r} must use htp.kernel.buffer(...) or htp.kernel.scalar(...) annotation"
            )
        values.append(KernelValue(parameter_name))
    trace = _ProgramTrace(tasks=[], dependencies=[], channels=[])
    token = _PROGRAM_TRACE.set(trace)
    try:
        function(*values)
    finally:
        _PROGRAM_TRACE.reset(token)
    if trace.seen_kernel is None:
        raise ValueError(f"Traced program {function.__name__!r} did not record any htp.routine.call(...) sites")
    return ProgramSpec(
        entry=function.__name__,
        kernel=trace.seen_kernel,
        tasks=tuple(trace.tasks),
        dependencies=tuple(trace.dependencies),
        channels=tuple(trace.channels),
        target=_normalize_target(target),
    )


def _normalize_target(target: dict[str, Any] | str | None) -> dict[str, Any]:
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
    return value


def _resolve_annotation(annotation: Any, *, function: Callable[..., Any]) -> Any:
    if isinstance(annotation, str):
        return eval(annotation, function.__globals__, function.__globals__)
    return annotation


__all__ = [
    "ChannelSpec",
    "DependencySpec",
    "KernelCallSpec",
    "ProgramSpec",
    "TaskHandle",
    "call",
    "channel",
    "dependency",
    "fifo_channel",
    "kernel_call",
    "program",
]
