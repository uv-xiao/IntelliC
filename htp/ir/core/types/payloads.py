from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from .model import (
    BufferType,
    ChannelType,
    DimExpr,
    IndexType,
    ScalarType,
    ShapeExpr,
    TensorType,
    TileType,
    TokenType,
    ViewType,
)


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


__all__ = ["type_to_payload"]
