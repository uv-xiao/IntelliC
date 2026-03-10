"""Public type helpers for human-first HTP authoring surfaces.

This module is intentionally small and ergonomic. It gives authors structured
dtype, dimension, shape, channel, and distribution objects without forcing them
to construct the lower-level staged payloads directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DType:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Dim:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Shape:
    dims: tuple[str | int, ...]


@dataclass(frozen=True)
class DistributionDim:
    kind: str
    axis: int | str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {"kind": self.kind}
        if self.axis is not None:
            payload["axis"] = self.axis
        return payload


@dataclass(frozen=True)
class TensorType:
    dtype: DType
    shape: Shape
    memory_space: str | None = None
    axis_layout: tuple[str, ...] = ()
    distribution: tuple[DistributionDim, ...] = ()
    kind: str = "tensor"


@dataclass(frozen=True)
class ChannelType:
    dtype: DType
    capacity: int | None
    protocol: str = "fifo"


bool_ = DType("bool")
i8 = DType("i8")
i16 = DType("i16")
i32 = DType("i32")
i64 = DType("i64")
u8 = DType("u8")
u16 = DType("u16")
u32 = DType("u32")
u64 = DType("u64")
f16 = DType("f16")
bf16 = DType("bf16")
f32 = DType("f32")
f64 = DType("f64")
index = DType("index")


def dim(name: str) -> Dim:
    return Dim(str(name))


def shape(*dims: str | int | Dim) -> Shape:
    return Shape(tuple(_dim_name(item) for item in dims))


def replicate() -> DistributionDim:
    return DistributionDim("replicate")


def shard(*, axis: int | str) -> DistributionDim:
    return DistributionDim("shard", axis=axis)


def tensor(
    dtype: DType | str,
    shape_value: Shape | tuple[str | int | Dim, ...] | list[str | int | Dim],
    *,
    memory_space: str | None = None,
    axis_layout: tuple[str, ...] | list[str] = (),
    distribution: tuple[DistributionDim | str, ...] | list[DistributionDim | str] = (),
) -> TensorType:
    resolved_shape = shape_value if isinstance(shape_value, Shape) else shape(*shape_value)
    return TensorType(
        dtype=_dtype(dtype),
        shape=resolved_shape,
        memory_space=memory_space,
        axis_layout=tuple(str(item) for item in axis_layout),
        distribution=tuple(_distribution_dim(item) for item in distribution),
    )


def channel_type(dtype: DType | str, *, capacity: int | None, protocol: str = "fifo") -> ChannelType:
    return ChannelType(dtype=_dtype(dtype), capacity=capacity, protocol=protocol)


def dtype_name(value: DType | str) -> str:
    return _dtype(value).name


def dims_payload(value: Shape | tuple[str | int | Dim, ...] | list[str | int | Dim]) -> tuple[str, ...]:
    if isinstance(value, Shape):
        return tuple(str(item) for item in value.dims)
    return tuple(_dim_name(item) for item in value)


def distribution_payload(
    value: tuple[DistributionDim | str, ...] | list[DistributionDim | str] | None,
) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    return tuple(_distribution_dim(item).to_payload() for item in value)


def _dtype(value: DType | str) -> DType:
    if isinstance(value, DType):
        return value
    return DType(str(value))


def _dim_name(value: str | int | Dim) -> str | int:
    if isinstance(value, Dim):
        return value.name
    return value


def _distribution_dim(value: DistributionDim | str) -> DistributionDim:
    if isinstance(value, DistributionDim):
        return value
    return DistributionDim(str(value))


__all__ = [
    "ChannelType",
    "DType",
    "Dim",
    "DistributionDim",
    "Shape",
    "TensorType",
    "bf16",
    "bool_",
    "channel_type",
    "dim",
    "dims_payload",
    "distribution_payload",
    "dtype_name",
    "f16",
    "f32",
    "f64",
    "i8",
    "i16",
    "i32",
    "i64",
    "index",
    "replicate",
    "shape",
    "shard",
    "tensor",
    "u8",
    "u16",
    "u32",
    "u64",
]
