"""Public CSP authoring helpers.

The explicit payload path remains available for low-level tests, but public
examples should prefer traced Python via ``@csp.program(...)``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from inspect import signature
from typing import Any

from htp.compiler import parse_target
from htp.kernel import KernelArgSpec, KernelSpec, KernelValue


@dataclass(frozen=True)
class ChannelSpec:
    """Typed channel declaration for the CSP surface."""

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
class ProcessSpec:
    """A single CSP process in the public surface."""

    name: str
    task_id: str
    kernel: str
    args: tuple[str, ...]
    puts: tuple[dict[str, Any], ...]
    gets: tuple[dict[str, Any], ...]
    steps: tuple[dict[str, Any], ...] = ()

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "task_id": self.task_id,
            "kernel": self.kernel,
            "args": list(self.args),
            "puts": [dict(item) for item in self.puts],
            "gets": [dict(item) for item in self.gets],
        }
        if self.steps:
            payload["steps"] = [dict(item) for item in self.steps]
        return payload


@dataclass(frozen=True)
class CSPProgramSpec:
    """High-level CSP authoring surface accepted by ``compile_program``."""

    entry: str
    kernel: KernelSpec
    channels: tuple[ChannelSpec, ...]
    processes: tuple[ProcessSpec, ...]
    target: dict[str, Any]

    def to_program(self) -> dict[str, Any]:
        return {
            "entry": self.entry,
            "target": dict(self.target),
            "kernel": self.kernel.to_payload(),
            "csp": {
                "channels": [channel.to_payload() for channel in self.channels],
                "processes": [process.to_payload() for process in self.processes],
            },
        }


@dataclass
class _CSPTrace:
    channels: list[ChannelSpec]
    processes: list[ProcessSpec]
    seen_kernel: KernelSpec | None
    task_counts: dict[str, int]


_CSP_TRACE: ContextVar[_CSPTrace | None] = ContextVar("htp_csp_trace", default=None)


def channel(name: str, *, dtype: str, capacity: int, protocol: str = "fifo") -> ChannelSpec:
    spec = ChannelSpec(name=str(name), dtype=str(dtype), capacity=int(capacity), protocol=str(protocol))
    trace = _CSP_TRACE.get()
    if trace is not None:
        trace.channels.append(spec)
    return spec


def fifo(name: str, *, dtype: str, capacity: int) -> ChannelSpec:
    return channel(name, dtype=dtype, capacity=capacity, protocol="fifo")


def put(channel: str | ChannelSpec, *, count: int = 1) -> dict[str, Any]:
    return {"kind": "put", "channel": _channel_name(channel), "count": int(count)}


def get(channel: str | ChannelSpec, *, count: int = 1) -> dict[str, Any]:
    return {"kind": "get", "channel": _channel_name(channel), "count": int(count)}


def process(
    name: str,
    *,
    task_id: str | None = None,
    kernel: KernelSpec | str,
    args: Sequence[str | KernelValue] = (),
    puts: Sequence[Mapping[str, Any]] = (),
    gets: Sequence[Mapping[str, Any]] = (),
    steps: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any] | ProcessSpec:
    """Create a CSP process.

    Outside traced mode this returns an explicit payload dict. Inside traced
    ``@csp.program`` it records the process and returns its typed spec.
    """

    normalized_steps = [dict(item) for item in steps]
    if normalized_steps:
        derived_puts = [dict(item) for item in normalized_steps if str(item.get("kind")) == "put"]
        derived_gets = [dict(item) for item in normalized_steps if str(item.get("kind")) == "get"]
    else:
        derived_puts = [dict(item) for item in puts]
        derived_gets = [dict(item) for item in gets]
    trace = _CSP_TRACE.get()
    resolved_task_id = str(task_id or name)
    if trace is not None:
        if not isinstance(kernel, KernelSpec):
            raise TypeError("Traced CSP process(...) requires a KernelSpec, not only a kernel name.")
        if trace.seen_kernel is None:
            trace.seen_kernel = kernel
        elif trace.seen_kernel.name != kernel.name:
            raise ValueError("The current CSP public surface supports exactly one kernel per program.")
        if task_id is None:
            resolved_task_id = _auto_task_id(trace, str(name))
        spec = ProcessSpec(
            name=str(name),
            task_id=resolved_task_id,
            kernel=kernel.name,
            args=tuple(_ref(arg) for arg in args),
            puts=tuple(derived_puts),
            gets=tuple(derived_gets),
            steps=tuple(normalized_steps),
        )
        trace.processes.append(spec)
        return spec
    return {
        "name": str(name),
        "task_id": resolved_task_id,
        "kernel": kernel.name if isinstance(kernel, KernelSpec) else str(kernel),
        "args": [_ref(arg) for arg in args],
        "puts": derived_puts,
        "gets": derived_gets,
        **({"steps": normalized_steps} if normalized_steps else {}),
    }


def program(
    function: Callable[..., Any] | None = None,
    *,
    entry: str | None = None,
    kernel: Mapping[str, Any] | KernelSpec | None = None,
    channels: Sequence[Mapping[str, Any] | ChannelSpec] | None = None,
    processes: Sequence[Mapping[str, Any] | ProcessSpec] | None = None,
    target: Mapping[str, Any] | str | None = None,
) -> CSPProgramSpec | dict[str, Any] | Callable[[Callable[..., Any]], CSPProgramSpec]:
    if function is None and kernel is None and channels is None and processes is None:
        return lambda traced_function: _trace_program(traced_function, target=target)
    if (
        function is not None
        and callable(function)
        and kernel is None
        and channels is None
        and processes is None
    ):
        return _trace_program(function, target=target)
    if entry is None or kernel is None or channels is None or processes is None:
        raise TypeError(
            "csp.program(...) expects either decorator usage or explicit entry=, kernel=, channels=, and processes="
        )
    return {
        "entry": entry,
        "target": _normalize_target(target),
        "kernel": kernel.to_payload() if isinstance(kernel, KernelSpec) else dict(kernel),
        "csp": {
            "channels": [_channel_payload(item) for item in channels],
            "processes": [_process_payload(item) for item in processes],
        },
    }


def _trace_program(function: Callable[..., Any], *, target: Mapping[str, Any] | str | None) -> CSPProgramSpec:
    values = _annotated_values(function)
    token = _CSP_TRACE.set(_CSPTrace(channels=[], processes=[], seen_kernel=None, task_counts={}))
    try:
        function(*values)
        trace = _CSP_TRACE.get()
    finally:
        _CSP_TRACE.reset(token)
    if trace is None or trace.seen_kernel is None:
        raise ValueError(
            f"Traced CSP program {function.__name__!r} did not record any csp.process(...) sites"
        )
    return CSPProgramSpec(
        entry=function.__name__,
        kernel=trace.seen_kernel,
        channels=tuple(trace.channels),
        processes=tuple(trace.processes),
        target=_normalize_target(target),
    )


def _annotated_values(function: Callable[..., Any]) -> list[KernelValue]:
    values: list[KernelValue] = []
    for parameter_name, parameter in signature(function).parameters.items():
        annotation = _resolve_annotation(parameter.annotation, function=function)
        if not isinstance(annotation, KernelArgSpec):
            raise TypeError(
                f"Traced CSP parameter {parameter_name!r} must use htp.kernel.buffer(...) or htp.kernel.scalar(...) annotation"
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


def _channel_name(value: str | ChannelSpec) -> str:
    if isinstance(value, ChannelSpec):
        return value.name
    return str(value)


def _channel_payload(item: Mapping[str, Any] | ChannelSpec) -> dict[str, Any]:
    if isinstance(item, ChannelSpec):
        return item.to_payload()
    return dict(item)


def _process_payload(item: Mapping[str, Any] | ProcessSpec) -> dict[str, Any]:
    if isinstance(item, ProcessSpec):
        return item.to_payload()
    return dict(item)


def _ref(value: str | KernelValue) -> str:
    if isinstance(value, KernelValue):
        return value.name
    return str(value)


def _auto_task_id(trace: _CSPTrace, process_name: str) -> str:
    index = trace.task_counts.get(process_name, 0)
    trace.task_counts[process_name] = index + 1
    return process_name if index == 0 else f"{process_name}_{index}"


__all__ = [
    "CSPProgramSpec",
    "ChannelSpec",
    "ProcessSpec",
    "channel",
    "fifo",
    "get",
    "process",
    "program",
    "put",
]
