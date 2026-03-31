"""CSP authoring helpers and builder surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from inspect import signature
from typing import Any

from htp.compiler import parse_target
from htp.ir.frontend import FrontendWorkload, build_frontend_program_module, kernel_spec_from_payload
from htp.ir.module import ProgramModule
from htp.ir.semantics import WorkloadTask
from htp.kernel import KernelSpec, KernelValue


class CSPBoundArgs:
    """Named kernel-argument bindings exposed to CSP authored programs."""

    def __init__(self, values: Mapping[str, KernelValue]):
        self._values = dict(values)

    def __getattr__(self, name: str) -> KernelValue:
        try:
            return self._values[name]
        except KeyError as exc:  # pragma: no cover - defensive surface
            raise AttributeError(name) from exc

    def ordered(self, names: Sequence[str] | None = None) -> tuple[KernelValue, ...]:
        if names is None:
            return tuple(self._values[name] for name in self._values)
        return tuple(self._values[name] for name in names)


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
    role: str | None = None,
) -> dict[str, Any]:
    normalized_steps = [dict(item) for item in steps]
    if normalized_steps:
        derived_puts = [dict(item) for item in normalized_steps if str(item.get("kind")) == "put"]
        derived_gets = [dict(item) for item in normalized_steps if str(item.get("kind")) == "get"]
    else:
        derived_puts = [dict(item) for item in puts]
        derived_gets = [dict(item) for item in gets]
    payload = {
        "name": str(name),
        "task_id": str(task_id),
        "kernel": kernel.name if isinstance(kernel, KernelSpec) else str(kernel),
        "args": [_ref(arg) for arg in args],
        "puts": derived_puts,
        "gets": derived_gets,
        **({"steps": normalized_steps} if normalized_steps else {}),
    }
    if role is not None:
        payload["role"] = str(role)
    return payload


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

    def to_program_module(self) -> ProgramModule:
        return build_csp_program_module(self)


def build_csp_program_module(spec: CSPProgramSpec) -> ProgramModule:
    authored_program = spec.to_program()
    kernel_spec = kernel_spec_from_payload(spec.kernel)
    kernel_module = kernel_spec.to_program_module()
    workload = FrontendWorkload(
        entry=spec.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=str(process["task_id"]),
                kind="process",
                kernel=str(process["kernel"]),
                args=tuple(str(arg) for arg in process.get("args", ())),
                entity_id=f"{spec.entry}:{process['task_id']}",
                attrs={
                    "name": str(process["name"]),
                    **({"role": str(process["role"])} if process.get("role") is not None else {}),
                },
            )
            for process in spec.processes
        ),
        channels=tuple(dict(item) for item in spec.channels),
        dependencies=(),
        processes=tuple(dict(item) for item in spec.processes),
        routine={
            "kind": "csp",
            "entry": spec.entry,
            "target": dict(spec.target),
        },
    )
    return build_frontend_program_module(
        kernel_module=kernel_module,
        authored_program=authored_program,
        workload=workload,
        source_surface="htp.csp.CSPProgramSpec",
        active_dialects=("htp.core", "htp.kernel", "htp.csp"),
    )


@dataclass
class CSPProcessBuilder:
    spec: dict[str, Any]

    def role(self, name: str) -> CSPProcessBuilder:
        self.spec["role"] = str(name)
        return self

    def put(self, channel: str | ChannelRef, *, count: int = 1) -> CSPProcessBuilder:
        self.spec.setdefault("steps", []).append(put(channel, count=count))
        self.spec["puts"] = [dict(item) for item in self.spec["steps"] if str(item.get("kind")) == "put"]
        return self

    def get(self, channel: str | ChannelRef, *, count: int = 1) -> CSPProcessBuilder:
        self.spec.setdefault("steps", []).append(get(channel, count=count))
        self.spec["gets"] = [dict(item) for item in self.spec["steps"] if str(item.get("kind")) == "get"]
        return self

    def compute(self, name: str, **attrs: Any) -> CSPProcessBuilder:
        self.spec.setdefault("steps", []).append(
            {
                "kind": "compute",
                "name": str(name),
                **{key: _step_value(value) for key, value in attrs.items()},
            }
        )
        return self

    def compute_step(self, op: str, /, **attrs: Any) -> CSPProcessBuilder:
        self.spec.setdefault("steps", []).append(
            {
                "kind": "compute",
                "op": str(op),
                **{key: _step_value(value) for key, value in attrs.items()},
            }
        )
        return self


@dataclass
class CSPBuilder:
    entry: str
    kernel_spec: KernelSpec
    target: dict[str, Any]
    channels: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    args: CSPBoundArgs = field(init=False)

    def __post_init__(self) -> None:
        bound_values = {
            argument.name: KernelValue(
                name=argument.name,
                dtype=argument.dtype,
                shape=argument.shape,
                kind=argument.kind,
                role=argument.role,
                memory_space=argument.memory_space,
                axis_layout=argument.axis_layout,
                distribution=argument.distribution,
                attrs=None if argument.attrs is None else dict(argument.attrs),
            )
            for argument in self.kernel_spec.args
            if argument.name is not None
        }
        self.args = CSPBoundArgs(bound_values)

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
        kernel: KernelSpec | str | None = None,
        args: Sequence[str | KernelValue] = (),
    ) -> CSPProcessBuilder:
        resolved_kernel = self.kernel_spec if kernel is None else kernel
        resolved_args = args or self._default_args_for(resolved_kernel)
        spec = process(name, task_id=task_id, kernel=resolved_kernel, args=resolved_args)
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

    def _default_args_for(self, kernel: KernelSpec | str) -> tuple[KernelValue, ...]:
        kernel_name = kernel.name if isinstance(kernel, KernelSpec) else str(kernel)
        if kernel_name != self.kernel_spec.name:
            return ()
        return self.args.ordered()


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


def _step_value(value: Any) -> Any:
    if isinstance(value, KernelValue):
        return value.name
    if isinstance(value, ChannelRef):
        return value.name
    return value


__all__ = [
    "CSPBuilder",
    "CSPProcessBuilder",
    "CSPProgramSpec",
    "ChannelRef",
    "build_csp_program_module",
    "channel",
    "fifo",
    "get",
    "process",
    "program",
    "put",
]
