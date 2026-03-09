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


def type_to_payload(value: Any) -> Any:
    if is_dataclass(value):
        payload = {
            field.name: type_to_payload(getattr(value, field.name))
            for field in fields(value)
            if getattr(value, field.name) is not None or field.name == "alias_of"
        }
        return _decorate_dataclass_payload(value, payload)
    if isinstance(value, dict):
        return {str(key): type_to_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [type_to_payload(item) for item in value]
    return value


def _decorate_dataclass_payload(value: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, ScalarType):
        payload["kind"] = "scalar"
    elif isinstance(value, IndexType):
        payload["kind"] = "index"
    elif isinstance(value, DimExpr):
        if value.kind != "const":
            payload.pop("value", None)
        if value.kind != "symbol":
            payload.pop("symbol", None)
    elif isinstance(value, ShapeExpr):
        payload["kind"] = "shape"
    elif isinstance(value, BufferType):
        payload["kind"] = "buffer"
    elif isinstance(value, ViewType):
        payload["kind"] = "view"
    elif isinstance(value, TensorType):
        payload["kind"] = "tensor"
    elif isinstance(value, TileType):
        payload["kind"] = "tile"
    elif isinstance(value, TokenType):
        payload["kind"] = "async_token"
    elif isinstance(value, ChannelType):
        payload["kind"] = "channel"
    return payload


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
    "type_to_payload",
]
