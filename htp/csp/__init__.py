"""CSP authoring helpers and builder surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from inspect import signature
from typing import Any

from htp.compiler import parse_target
from htp.kernel import KernelSpec, KernelValue


@dataclass(frozen=True)
class ChannelRef:
    name: str
    dtype: str
    capacity: int
    protocol: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "capacity": self.capacity,
            "protocol": self.protocol,
        }


def channel(name: str, *, dtype: str, capacity: int, protocol: str = "fifo") -> dict[str, Any]:
    return {
        "name": str(name),
        "dtype": str(dtype),
        "capacity": int(capacity),
        "protocol": str(protocol),
    }


def fifo(name: str, *, dtype: str, capacity: int) -> dict[str, Any]:
    return channel(name, dtype=dtype, capacity=capacity, protocol="fifo")


def put(channel: str | ChannelRef, *, count: int = 1) -> dict[str, Any]:
    return {"kind": "put", "channel": _channel_name(channel), "count": int(count)}


def get(channel: str | ChannelRef, *, count: int = 1) -> dict[str, Any]:
    return {"kind": "get", "channel": _channel_name(channel), "count": int(count)}


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


@dataclass(frozen=True)
class CSPProgramSpec:
    entry: str
    target: dict[str, Any]
    kernel: dict[str, Any]
    channels: tuple[dict[str, Any], ...]
    processes: tuple[dict[str, Any], ...]

    def to_program(self) -> dict[str, Any]:
        return {
            "entry": self.entry,
            "target": dict(self.target),
            "kernel": dict(self.kernel),
            "csp": {
                "channels": [dict(item) for item in self.channels],
                "processes": [dict(item) for item in self.processes],
            },
        }


@dataclass
class CSPProcessBuilder:
    spec: dict[str, Any]

    def put(self, channel: str | ChannelRef, *, count: int = 1) -> CSPProcessBuilder:
        self.spec.setdefault("steps", []).append(put(channel, count=count))
        self.spec["puts"] = [dict(item) for item in self.spec["steps"] if str(item.get("kind")) == "put"]
        return self

    def get(self, channel: str | ChannelRef, *, count: int = 1) -> CSPProcessBuilder:
        self.spec.setdefault("steps", []).append(get(channel, count=count))
        self.spec["gets"] = [dict(item) for item in self.spec["steps"] if str(item.get("kind")) == "get"]
        return self


@dataclass
class CSPBuilder:
    entry: str
    kernel_spec: KernelSpec
    target: dict[str, Any]
    channels: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)

    def channel(self, name: str, *, dtype: str, capacity: int, protocol: str = "fifo") -> ChannelRef:
        ref = ChannelRef(name=str(name), dtype=str(dtype), capacity=int(capacity), protocol=str(protocol))
        self.channels.append(ref.to_payload())
        return ref

    def fifo(self, name: str, *, dtype: str, capacity: int) -> ChannelRef:
        return self.channel(name, dtype=dtype, capacity=capacity, protocol="fifo")

    def process(
        self,
        name: str,
        *,
        task_id: str,
        kernel: KernelSpec | str,
        args: Sequence[str | KernelValue] = (),
    ) -> CSPProcessBuilder:
        spec = process(name, task_id=task_id, kernel=kernel, args=args)
        self.processes.append(spec)
        return CSPProcessBuilder(spec)

    def to_program(self) -> dict[str, Any]:
        return CSPProgramSpec(
            entry=self.entry,
            target=self.target,
            kernel=self.kernel_spec.to_payload(),
            channels=tuple(self.channels),
            processes=tuple(self.processes),
        ).to_program()


def program(
    *,
    entry: str | None = None,
    kernel: Mapping[str, Any] | KernelSpec,
    channels: Sequence[Mapping[str, Any]] | None = None,
    processes: Sequence[Mapping[str, Any]] | None = None,
    target: Mapping[str, Any] | str | None = None,
) -> dict[str, Any] | Callable[[Callable[..., Any]], CSPProgramSpec]:
    if channels is not None or processes is not None or entry is not None and isinstance(kernel, Mapping):
        if entry is None:
            raise TypeError(
                "csp.program(..., kernel=<mapping>, ...) requires entry= when used as a payload builder."
            )
        return {
            "entry": entry,
            "target": _normalize_target(target),
            "kernel": kernel.to_payload() if isinstance(kernel, KernelSpec) else dict(kernel),
            "csp": {
                "channels": [dict(item) for item in (channels or ())],
                "processes": [dict(item) for item in (processes or ())],
            },
        }

    if not isinstance(kernel, KernelSpec):
        raise TypeError("Decorator-form csp.program(...) requires kernel=<KernelSpec>.")

    def decorator(function: Callable[..., Any]) -> CSPProgramSpec:
        builder = CSPBuilder(
            entry=entry or function.__name__, kernel_spec=kernel, target=_normalize_target(target)
        )
        if len(signature(function).parameters) == 0:
            function()
        else:
            function(builder)
        return CSPProgramSpec(
            entry=builder.entry,
            target=builder.target,
            kernel=builder.kernel_spec.to_payload(),
            channels=tuple(builder.channels),
            processes=tuple(builder.processes),
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


def _channel_name(channel: str | ChannelRef) -> str:
    if isinstance(channel, ChannelRef):
        return channel.name
    return str(channel)


__all__ = [
    "CSPBuilder",
    "CSPProcessBuilder",
    "CSPProgramSpec",
    "ChannelRef",
    "channel",
    "fifo",
    "get",
    "process",
    "program",
    "put",
]
