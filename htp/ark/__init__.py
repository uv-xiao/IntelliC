"""Arknife-inspired authoring surface integrated with HTP's core pipeline.

The point of this module is not to embed Arknife as a sidecar compiler. It
provides the same explicit-hierarchy technique classes inside HTP:

- hardware profiles with parallel levels and memory spaces
- explicit channels and instruction-oriented steps
- a Python-native context-manager authoring surface

Programs authored here still lower into HTP's canonical `to_program()` payload
and run through the normal passes, replay flow, solver, and backend bindings.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any

from htp.compiler import parse_target


@dataclass(frozen=True)
class Axis:
    name: str
    extent: int

    def to_payload(self) -> dict[str, Any]:
        return {"name": self.name, "extent": self.extent}


@dataclass(frozen=True)
class MemorySpace:
    name: str
    alignment: int | None = None
    capacity: int | None = None
    auto_alloc: bool = False


@dataclass(frozen=True)
class ParallelLevel:
    name: str
    memory_spaces: tuple[str, ...]
    units: int | None = None
    sizes: tuple[int, ...] = ()


@dataclass(frozen=True)
class HardwareProfile:
    name: str
    backend: str
    option: str
    hardware_profile: str
    memory_spaces: tuple[MemorySpace, ...]
    parallelism_levels: tuple[ParallelLevel, ...]
    capabilities: tuple[str, ...]
    default_channels: tuple[dict[str, Any], ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "backend": self.backend,
            "profile": self.option,
            "hardware_profile": self.hardware_profile,
            "memory_spaces": [space.name for space in self.memory_spaces],
            "memory_space_info": [asdict(space) for space in self.memory_spaces],
            "parallelism_levels": [level.name for level in self.parallelism_levels],
            "parallelism_level_info": [asdict(level) for level in self.parallelism_levels],
            "capabilities": list(self.capabilities),
            "channels": [dict(item) for item in self.default_channels],
        }


@dataclass(frozen=True)
class Tensor:
    name: str
    dtype: str
    shape: tuple[str, ...]
    memory: str
    role: str | None = None

    def to_arg_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "kind": "buffer",
            "dtype": self.dtype,
            "shape": list(self.shape),
            "memory_space": self.memory,
        }
        if self.role is not None:
            payload["role"] = self.role
        return payload


@dataclass(frozen=True)
class Channel:
    name: str
    scope: str
    memory: str
    kind: str = "barrier"
    slots: int = 1

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "scope": self.scope,
            "memory": self.memory,
            "kind": self.kind,
            "slots": self.slots,
        }


@dataclass
class _Region:
    kind: str
    attrs: dict[str, Any]


@dataclass
class _ArkTrace:
    function_name: str
    hardware: HardwareProfile
    target: dict[str, Any]
    tensors: dict[str, Tensor] = field(default_factory=dict)
    channels: dict[str, Channel] = field(default_factory=dict)
    ops: list[dict[str, Any]] = field(default_factory=list)
    regions: list[_Region] = field(default_factory=list)

    def region_path(self) -> list[dict[str, Any]]:
        return [{"kind": item.kind, **dict(item.attrs)} for item in self.regions]

    def add_op(self, payload: dict[str, Any]) -> None:
        op_payload = dict(payload)
        op_payload.setdefault("attrs", {})
        attrs = dict(op_payload["attrs"])
        attrs.setdefault("regions", self.region_path())
        op_payload["attrs"] = attrs
        self.ops.append(op_payload)


@dataclass(frozen=True)
class ProgramSpec:
    entry: str
    target: dict[str, Any]
    hardware: HardwareProfile
    args: tuple[Tensor, ...]
    channels: tuple[Channel, ...]
    ops: tuple[dict[str, Any], ...]

    def to_program(self) -> dict[str, Any]:
        hardware_payload = self.hardware.to_payload()
        channels_payload = [channel.to_payload() for channel in self.channels]
        instruction_catalog = _instruction_catalog(self.ops)
        shape_args = _shape_arg_payloads(self.args)
        kernel_args = [item.to_arg_payload() for item in self.args] + shape_args
        runtime_arg_names = [item.name for item in self.args] + [item["name"] for item in shape_args]
        return {
            "entry": self.entry,
            "target": dict(self.target),
            "kernel": {
                "name": self.entry,
                "args": kernel_args,
                "ops": [dict(op) for op in self.ops],
            },
            "workload": {
                "entry": self.entry,
                "tasks": [
                    {
                        "task_id": f"{self.entry}_main",
                        "kind": "kernel_call",
                        "kernel": self.entry,
                        "args": runtime_arg_names,
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
            "ark": {
                "hardware": hardware_payload,
                "channels": channels_payload,
                "instructions": instruction_catalog,
            },
        }


_TRACE: ContextVar[_ArkTrace | None] = ContextVar("htp_ark_trace", default=None)


def ampere() -> HardwareProfile:
    return HardwareProfile(
        name="ampere",
        backend="nvgpu",
        option="ampere",
        hardware_profile="nvidia:ampere:sm80",
        memory_spaces=(
            MemorySpace("global"),
            MemorySpace("shared", alignment=128, capacity=163840),
            MemorySpace("register", auto_alloc=True, capacity=256 * 1024),
        ),
        parallelism_levels=(
            ParallelLevel("lane", ("register",), units=32),
            ParallelLevel("warp", (), units=4),
            ParallelLevel("block", ("shared",), units=1),
            ParallelLevel("grid", ("global",), units=1),
        ),
        capabilities=("cp.async", "ldmatrix", "mma.sync"),
        default_channels=(
            {"name": "shared_pipe", "scope": "block", "memory": "shared", "kind": "barrier", "slots": 3},
        ),
    )


def blackwell() -> HardwareProfile:
    return HardwareProfile(
        name="blackwell",
        backend="nvgpu",
        option="blackwell",
        hardware_profile="nvidia:blackwell:sm100",
        memory_spaces=(
            MemorySpace("global"),
            MemorySpace("shared", alignment=128, capacity=262144),
            MemorySpace("tensor", alignment=512, capacity=262144),
            MemorySpace("register", auto_alloc=True, capacity=256 * 1024),
        ),
        parallelism_levels=(
            ParallelLevel("lane", ("register",), units=32),
            ParallelLevel("warp", (), units=4),
            ParallelLevel("warpgroup", (), units=2),
            ParallelLevel("block", ("shared", "tensor"), units=2),
            ParallelLevel("cluster", (), units=1),
            ParallelLevel("grid", ("global",), units=1),
        ),
        capabilities=("cp.async.bulk", "tma", "wgmma"),
        default_channels=(
            {"name": "cluster_pipe", "scope": "cluster", "memory": "shared", "kind": "barrier", "slots": 2},
            {"name": "store_pipe", "scope": "cluster", "memory": "shared", "kind": "tma_store", "slots": 2},
        ),
    )


def axis(name: str, extent: int) -> Axis:
    return Axis(name=name, extent=int(extent))


def tensor(
    name: str,
    *,
    dtype: str,
    shape: Sequence[str | Axis],
    memory: str,
    role: str | None = None,
) -> Tensor:
    trace = _require_trace("tensor")
    shape_dims = tuple(_dim_name(item) for item in shape)
    ret = Tensor(name=name, dtype=dtype, shape=shape_dims, memory=memory, role=role)
    trace.tensors[name] = ret
    return ret


def channel(name: str, *, scope: str, memory: str, kind: str = "barrier", slots: int = 1) -> Channel:
    trace = _require_trace("channel")
    ret = Channel(name=name, scope=scope, memory=memory, kind=kind, slots=int(slots))
    trace.channels[name] = ret
    return ret


def build(*, target: str, hardware: HardwareProfile) -> Callable[[Callable[..., Iterable[Tensor] | None]], ProgramSpec]:
    target_spec = parse_target(target)
    normalized_target = {"backend": target_spec.backend}
    if target_spec.option is not None:
        normalized_target["option"] = target_spec.option

    def decorator(function: Callable[..., Iterable[Tensor] | None]) -> ProgramSpec:
        trace = _ArkTrace(function_name=function.__name__, hardware=hardware, target=normalized_target)
        token = _TRACE.set(trace)
        try:
            returned = function()
        finally:
            _TRACE.reset(token)
        if normalized_target.get("backend") != hardware.backend or normalized_target.get("option") != hardware.option:
            raise ValueError(
                f"Arknife surface target {normalized_target!r} must match hardware profile "
                f"{hardware.backend}-{hardware.option!s}."
            )
        args = _normalize_returned_tensors(trace, returned)
        channels = tuple(trace.channels.values()) if trace.channels else tuple(
            Channel(**item) for item in hardware.default_channels
        )
        return ProgramSpec(
            entry=function.__name__,
            target=normalized_target,
            hardware=hardware,
            args=args,
            channels=channels,
            ops=tuple(trace.ops),
        )

    return decorator


@contextmanager
def spatial(level: str, *axes: Axis, swizzle: list[int | None] | None = None):
    trace = _require_trace("spatial")
    region = _Region(
        kind="spatial",
        attrs={
            "level": level,
            "axes": [item.to_payload() for item in axes],
            **({"swizzle": list(swizzle)} if swizzle is not None else {}),
        },
    )
    trace.regions.append(region)
    try:
        yield
    finally:
        trace.regions.pop()


@contextmanager
def temporal(*axes: Axis, unroll: bool = False):
    trace = _require_trace("temporal")
    region = _Region(
        kind="temporal",
        attrs={
            "axes": [item.to_payload() for item in axes],
            "unroll": bool(unroll),
        },
    )
    trace.regions.append(region)
    try:
        yield
    finally:
        trace.regions.pop()


@contextmanager
def pipeline(axis: Axis, *, stages: int, unroll: bool = False):
    trace = _require_trace("pipeline")
    region = _Region(
        kind="pipeline",
        attrs={"axis": axis.to_payload(), "stages": int(stages), "unroll": bool(unroll)},
    )
    trace.regions.append(region)
    try:
        yield
    finally:
        trace.regions.pop()


@contextmanager
def sequence():
    trace = _require_trace("sequence")
    trace.regions.append(_Region(kind="sequence", attrs={}))
    try:
        yield
    finally:
        trace.regions.pop()


def cp_async(dst: Tensor, src: Tensor, *, channel: str | Channel | None = None) -> None:
    _instruction_op(
        "cp_async",
        target=dst,
        source=src,
        capability="cp.async",
        channel=channel,
    )


def ldmatrix(dst: Tensor, src: Tensor, *, transpose: bool = False) -> None:
    _instruction_op(
        "ldmatrix",
        target=dst,
        source=src,
        capability="ldmatrix",
        transpose=bool(transpose),
    )


def mma_sync(
    dst: Tensor,
    lhs: Tensor,
    rhs: Tensor,
    *,
    accum: Tensor | None = None,
    shape: tuple[int, int, int] = (16, 8, 16),
) -> None:
    _instruction_op(
        "mma_sync",
        out=dst,
        lhs=lhs,
        rhs=rhs,
        accum=accum or dst,
        capability="mma.sync",
        instruction_shape=list(shape),
    )


def tma_load(dst: Tensor, src: Tensor, *, channel: str | Channel | None = None) -> None:
    _instruction_op(
        "tma_load",
        target=dst,
        source=src,
        capability="tma",
        channel=channel,
    )


def wgmma(
    dst: Tensor,
    lhs: Tensor,
    rhs: Tensor,
    *,
    accum: Tensor | None = None,
    shape: tuple[int, int, int] = (64, 128, 16),
    channel: str | Channel | None = None,
) -> None:
    _instruction_op(
        "wgmma",
        out=dst,
        lhs=lhs,
        rhs=rhs,
        accum=accum or dst,
        capability="wgmma",
        channel=channel,
        instruction_shape=list(shape),
    )


def tma_store(dst: Tensor, src: Tensor, *, channel: str | Channel | None = None) -> None:
    _instruction_op(
        "tma_store",
        target=dst,
        source=src,
        capability="tma",
        channel=channel,
    )


def commit(dst: Tensor, src: Tensor) -> None:
    _instruction_op("commit", target=dst, value=src)


def _instruction_op(name: str, **payload: Any) -> None:
    trace = _require_trace(name)
    attrs = {
        "instruction": name,
        "hardware_profile": trace.hardware.hardware_profile,
    }
    normalized: dict[str, Any] = {"op": name, "attrs": attrs}
    for key, value in payload.items():
        if isinstance(value, Tensor):
            normalized[key] = value.name
            if key in {"target", "out"}:
                attrs[f"{key}_memory"] = value.memory
                attrs.setdefault("shape", list(value.shape))
            elif key in {"source", "lhs", "rhs", "value", "accum"}:
                attrs[f"{key}_memory"] = value.memory
        elif isinstance(value, Channel):
            normalized[key] = value.name
            attrs["channel_scope"] = value.scope
        elif value is not None:
            normalized[key] = value
            attrs[key] = value
    trace.add_op(normalized)


def _instruction_catalog(ops: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []
    known: set[tuple[str, str | None]] = set()
    for op in ops:
        attrs = dict(op.get("attrs", {}))
        item = {
            "instruction": str(attrs.get("instruction", op.get("op", ""))),
            **({"capability": str(op["capability"])} if op.get("capability") is not None else {}),
        }
        key = (item["instruction"], item.get("capability"))
        if key in known:
            continue
        known.add(key)
        seen.append(item)
    return seen


def _normalize_returned_tensors(
    trace: _ArkTrace, returned: Iterable[Tensor] | None
) -> tuple[Tensor, ...]:
    if returned is None:
        args = tuple(item for item in trace.tensors.values() if item.role is not None)
    else:
        args = tuple(item for item in returned if isinstance(item, Tensor))
    if not args:
        raise ValueError("Arknife surface build functions must return the public input/output tensors.")
    return args


def _shape_arg_payloads(args: Sequence[Tensor]) -> list[dict[str, Any]]:
    names: list[str] = []
    for tensor in args:
        for dim in tensor.shape:
            if dim.isidentifier() and dim not in names:
                names.append(dim)
    return [
        {
            "name": name,
            "kind": "scalar",
            "dtype": "i32",
            "shape": [],
            "role": "shape",
        }
        for name in names
    ]


def _dim_name(value: str | Axis) -> str:
    if isinstance(value, Axis):
        return value.name
    return str(value)


def _require_trace(name: str) -> _ArkTrace:
    trace = _TRACE.get()
    if trace is None:
        raise RuntimeError(f"htp.ark.{name} can only be used inside @htp.ark.build functions.")
    return trace


__all__ = [
    "Axis",
    "Channel",
    "HardwareProfile",
    "MemorySpace",
    "ParallelLevel",
    "ProgramSpec",
    "Tensor",
    "ampere",
    "axis",
    "blackwell",
    "build",
    "channel",
    "commit",
    "cp_async",
    "ldmatrix",
    "mma_sync",
    "pipeline",
    "sequence",
    "spatial",
    "temporal",
    "tensor",
    "tma_load",
    "tma_store",
    "wgmma",
]
