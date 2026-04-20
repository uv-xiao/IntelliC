"""CSP authoring helpers and builder surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from inspect import signature
from typing import Any

from htp.compiler import parse_target
from htp.ir.dialects.csp import (
    CSPComputeStep,
    CSPGetStep,
    CSPProcessStep,
    CSPPutStep,
    steps_from_payload,
    steps_to_payload,
)
from htp.ir.frontends import resolve_frontend
from htp.ir.program.module import ProgramModule
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


@dataclass
class CSPProcessSpec:
    name: str
    task_id: str
    kernel: str
    args: tuple[str, ...]
    steps: list[CSPProcessStep] = field(default_factory=list)
    role: str | None = None

    def to_payload(self) -> dict[str, Any]:
        normalized_steps = steps_to_payload(self.steps)
        puts = [dict(item) for item in normalized_steps if str(item.get("kind")) == "put"]
        gets = [dict(item) for item in normalized_steps if str(item.get("kind")) == "get"]
        payload = {
            "name": self.name,
            "task_id": self.task_id,
            "kernel": self.kernel,
            "args": list(self.args),
            "puts": puts,
            "gets": gets,
        }
        if normalized_steps:
            payload["steps"] = normalized_steps
        if self.role is not None:
            payload["role"] = self.role
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> CSPProcessSpec:
        normalized_steps = steps_from_payload(payload.get("steps", ()))
        if not normalized_steps:
            normalized_steps = [
                *steps_from_payload(payload.get("gets", ())),
                *steps_from_payload(payload.get("puts", ())),
            ]
        return cls(
            name=str(payload["name"]),
            task_id=str(payload["task_id"]),
            kernel=str(payload["kernel"]),
            args=tuple(str(arg) for arg in payload.get("args", ())),
            steps=list(normalized_steps),
            role=str(payload["role"]) if payload.get("role") is not None else None,
        )


def channel(name: str, *, dtype: str, capacity: int, protocol: str = "fifo") -> dict[str, Any]:
    return {
        "name": str(name),
        "dtype": str(dtype),
        "capacity": int(capacity),
        "protocol": str(protocol),
    }


def fifo(name: str, *, dtype: str, capacity: int) -> dict[str, Any]:
    return channel(name, dtype=dtype, capacity=capacity, protocol="fifo")


def put(channel: str | ChannelRef, value: Any | None = None, *, count: int = 1) -> dict[str, Any]:
    payload = {"kind": "put", "channel": _channel_name(channel), "count": int(count)}
    if value is not None:
        payload["value"] = _step_value(value)
    return payload


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
) -> CSPProcessSpec:
    derived_steps = steps_from_payload(steps)
    if not derived_steps:
        derived_steps = [
            *(
                CSPGetStep(
                    channel=str(_step_value(item["channel"])),
                    count=int(item.get("count", 1)),
                    attrs={
                        key: _step_value(value)
                        for key, value in item.items()
                        if key not in {"channel", "count"}
                    },
                )
                for item in gets
            ),
            *(
                CSPPutStep(
                    channel=str(_step_value(item["channel"])),
                    count=int(item.get("count", 1)),
                    value=_step_value(item.get("value")) if item.get("value") is not None else None,
                    attrs={
                        key: _step_value(value)
                        for key, value in item.items()
                        if key not in {"channel", "count", "value"}
                    },
                )
                for item in puts
            ),
        ]
    return CSPProcessSpec(
        name=str(name),
        task_id=str(task_id),
        kernel=kernel.name if isinstance(kernel, KernelSpec) else str(kernel),
        args=tuple(_ref(arg) for arg in args),
        steps=list(derived_steps),
        role=str(role) if role is not None else None,
    )


@dataclass(frozen=True)
class CSPProgramSpec:
    entry: str
    target: dict[str, Any]
    kernel: KernelSpec
    channels: tuple[ChannelRef, ...]
    processes: tuple[CSPProcessSpec, ...]
    authored_program: dict[str, Any] | None = None
    prebuilt_program_module: ProgramModule | None = None

    def to_program(self) -> dict[str, Any]:
        if self.authored_program is not None:
            return dict(self.authored_program)
        return {
            "entry": self.entry,
            "target": dict(self.target),
            "kernel": self.kernel.to_payload(),
            "csp": {
                "channels": [item.to_payload() for item in self.channels],
                "processes": [item.to_payload() for item in self.processes],
            },
        }

    def kernel_spec(self) -> KernelSpec:
        return self.kernel

    def to_program_module(self) -> ProgramModule:
        if self.prebuilt_program_module is not None:
            return self.prebuilt_program_module
        frontend = resolve_frontend(self)
        if frontend is None:  # pragma: no cover - defensive registry failure
            raise TypeError("No registered frontend for htp.csp.CSPProgramSpec")
        return frontend.build(self)


@dataclass
class CSPProcessBuilder:
    spec: CSPProcessSpec

    def role(self, name: str) -> CSPProcessBuilder:
        self.spec.role = str(name)
        return self

    def put(
        self,
        channel: str | ChannelRef,
        value: Any | None = None,
        *,
        count: int = 1,
    ) -> CSPProcessBuilder:
        self.spec.steps.append(
            CSPPutStep(
                channel=_channel_name(channel),
                count=count,
                value=_step_value(value) if value is not None else None,
            )
        )
        return self

    def get(self, channel: str | ChannelRef, *, count: int = 1) -> CSPProcessBuilder:
        self.spec.steps.append(CSPGetStep(channel=_channel_name(channel), count=count))
        return self

    def compute(self, name: str, **attrs: Any) -> CSPProcessBuilder:
        self.spec.steps.append(
            CSPProcessStep(
                kind="compute",
                attrs={"name": str(name), **{key: _step_value(value) for key, value in attrs.items()}},
            )
        )
        return self

    def compute_step(self, op: str, /, **attrs: Any) -> CSPProcessBuilder:
        return self._compute_op(str(op), attrs={key: _step_value(value) for key, value in attrs.items()})

    def __getattr__(self, op: str):
        if op.startswith("_"):
            raise AttributeError(op)

        def emit_compute(**attrs: Any) -> CSPProcessBuilder:
            return self._compute_op(op, attrs={key: _step_value(value) for key, value in attrs.items()})

        return emit_compute

    def _compute_op(self, op: str, *, attrs: Mapping[str, Any]) -> CSPProcessBuilder:
        self.spec.steps.append(CSPComputeStep(op=op, attrs=attrs))
        return self


@dataclass
class CSPBuilder:
    entry: str
    kernel_spec: KernelSpec
    target: dict[str, Any]
    channels: list[ChannelRef] = field(default_factory=list)
    processes: list[CSPProcessSpec] = field(default_factory=list)
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
        self.channels.append(ref)
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
            kernel=self.kernel_spec,
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
    channels: Sequence[Mapping[str, Any] | ChannelRef] | None = None,
    processes: Sequence[Mapping[str, Any] | CSPProcessSpec] | None = None,
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
                "channels": [
                    item.to_payload() if isinstance(item, ChannelRef) else dict(item)
                    for item in (channels or ())
                ],
                "processes": [
                    item.to_payload() if isinstance(item, CSPProcessSpec) else dict(item)
                    for item in (processes or ())
                ],
            },
        }

    if not isinstance(kernel, KernelSpec):
        raise TypeError("Decorator-form csp.program(...) requires kernel=<KernelSpec>.")

    def decorator(function: Callable[..., Any]) -> CSPProgramSpec:
        from htp.ir.dialects.csp import build_csp_ast_program_spec

        ast_spec = build_csp_ast_program_spec(
            function=function,
            kernel_spec=kernel,
            target=_normalize_target(target),
            entry=entry or function.__name__,
        )
        if ast_spec is not None:
            return ast_spec
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
            kernel=builder.kernel_spec,
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
    "CSPComputeStep",
    "CSPGetStep",
    "CSPProcessSpec",
    "CSPProcessStep",
    "CSPProcessBuilder",
    "CSPProgramSpec",
    "CSPPutStep",
    "ChannelRef",
    "channel",
    "fifo",
    "get",
    "process",
    "program",
    "put",
]
