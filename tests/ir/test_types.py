from __future__ import annotations

import pytest

from htp.ir.core.types import (
    BufferType,
    ChannelType,
    DimExpr,
    IndexType,
    ScalarType,
    ShapeExpr,
    TokenType,
    ViewType,
    dtype_from_name,
    shape_from_sequence,
    type_to_payload,
)


def test_type_to_payload_emits_structured_shapes_and_aliases():
    payload = type_to_payload(
        BufferType(
            dtype=ScalarType("f32"),
            shape=ShapeExpr((DimExpr.sym("M"), DimExpr.sym("K"))),
            space="global",
            alias_of=None,
        )
    )

    assert payload == {
        "kind": "buffer",
        "dtype": {"kind": "scalar", "name": "f32"},
        "shape": {
            "kind": "shape",
            "dims": [
                {"kind": "symbol", "symbol": "M"},
                {"kind": "symbol", "symbol": "K"},
            ],
        },
        "space": "global",
        "alias_of": None,
    }


def test_shape_from_sequence_accepts_symbolic_and_constant_dims():
    shape = shape_from_sequence(["M", 16, "tile_k"])

    assert type_to_payload(shape) == {
        "kind": "shape",
        "dims": [
            {"kind": "symbol", "symbol": "M"},
            {"kind": "const", "value": 16},
            {"kind": "symbol", "symbol": "tile_k"},
        ],
    }


def test_view_channel_and_token_types_have_first_class_value_kinds():
    assert type_to_payload(
        ViewType(
            dtype=ScalarType("f32"),
            shape=ShapeExpr((DimExpr.sym("N"),)),
            source="buffer_A",
            alias_of="buffer_A",
        )
    ) == {
        "kind": "view",
        "dtype": {"kind": "scalar", "name": "f32"},
        "shape": {
            "kind": "shape",
            "dims": [{"kind": "symbol", "symbol": "N"}],
        },
        "source": "buffer_A",
        "alias_of": "buffer_A",
    }
    assert type_to_payload(ChannelType(element=ScalarType("i32"), capacity=4, protocol="fifo")) == {
        "kind": "channel",
        "element": {"kind": "scalar", "name": "i32"},
        "capacity": 4,
        "protocol": "fifo",
    }
    assert type_to_payload(TokenType(token_kind="async_copy")) == {
        "kind": "async_token",
        "token_kind": "async_copy",
    }


def test_dtype_surface_validates_supported_scalars_and_index_type():
    assert type_to_payload(dtype_from_name("bf16")) == {"kind": "scalar", "name": "bf16"}
    assert type_to_payload(dtype_from_name("bool")) == {"kind": "scalar", "name": "bool"}
    assert type_to_payload(IndexType()) == {"kind": "index", "name": "index"}

    with pytest.raises(ValueError, match="Unsupported scalar dtype"):
        dtype_from_name("fp19")
