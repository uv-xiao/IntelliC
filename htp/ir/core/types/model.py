from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any

_SCALAR_DTYPES = {
    "bool",
    "i8",
    "i16",
    "i32",
    "i64",
    "u8",
    "u16",
    "u32",
    "u64",
    "f16",
    "bf16",
    "f32",
    "f64",
}


@dataclass(frozen=True)
class ScalarType:
    name: str


@dataclass(frozen=True)
class IndexType:
    name: str = "index"


@dataclass(frozen=True)
class DimExpr:
    kind: str
    value: int | None = None
    symbol: str | None = None

    @classmethod
    def const(cls, value: int) -> DimExpr:
        return cls(kind="const", value=int(value))

    @classmethod
    def sym(cls, name: str) -> DimExpr:
        return cls(kind="symbol", symbol=str(name))


@dataclass(frozen=True)
class ShapeExpr:
    dims: tuple[DimExpr, ...]


@dataclass(frozen=True)
class BufferType:
    dtype: ScalarType
    shape: ShapeExpr
    space: str
    alias_of: str | None = None


@dataclass(frozen=True)
class ViewType:
    dtype: ScalarType
    shape: ShapeExpr
    source: str
    alias_of: str


@dataclass(frozen=True)
class TensorType:
    dtype: ScalarType
    shape: ShapeExpr


@dataclass(frozen=True)
class TileType:
    dtype: ScalarType
    shape: ShapeExpr


@dataclass(frozen=True)
class TokenType:
    token_kind: str


@dataclass(frozen=True)
class ChannelType:
    element: ScalarType
    capacity: int | None
    protocol: str


def dtype_from_name(name: str) -> ScalarType | IndexType:
    normalized = str(name)
    if normalized == "index":
        return IndexType()
    if normalized not in _SCALAR_DTYPES:
        raise ValueError(f"Unsupported scalar dtype {normalized!r}")
    return ScalarType(normalized)


def dim_from_value(value: object) -> DimExpr:
    if isinstance(value, int):
        return DimExpr.const(value)
    return DimExpr.sym(str(value))


def shape_from_sequence(values: list[object] | tuple[object, ...]) -> ShapeExpr:
    return ShapeExpr(tuple(dim_from_value(value) for value in values))



__all__ = [
    "BufferType",
    "ChannelType",
    "DimExpr",
    "IndexType",
    "ScalarType",
    "ShapeExpr",
    "TensorType",
    "TileType",
    "TokenType",
    "ViewType",
    "dim_from_value",
    "dtype_from_name",
    "shape_from_sequence",
]
