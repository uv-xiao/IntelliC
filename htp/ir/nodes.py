from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class NodeId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class ItemId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class SymbolId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class RegionId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class Node:
    node_id: NodeId


@dataclass(frozen=True)
class Expr(Node):
    pass


@dataclass(frozen=True)
class Stmt(Node):
    pass


@dataclass(frozen=True)
class Item(Node):
    item_id: ItemId
    name: str


@dataclass(frozen=True)
class Parameter(Node):
    symbol_id: SymbolId
    name: str
    kind: str
    dtype: str


@dataclass(frozen=True)
class Ref(Expr):
    symbol_id: SymbolId
    name: str


@dataclass(frozen=True)
class LiteralExpr(Expr):
    value: int | float | bool


@dataclass(frozen=True)
class BinaryExpr(Expr):
    op: Literal["add", "sub", "mul", "div"]
    lhs: Expr
    rhs: Expr


@dataclass(frozen=True)
class Let(Stmt):
    symbol_id: SymbolId
    name: str
    value: Expr


@dataclass(frozen=True)
class Return(Stmt):
    value: Expr


@dataclass(frozen=True)
class Region(Node):
    region_id: RegionId
    statements: tuple[Stmt, ...]


@dataclass(frozen=True)
class Kernel(Item):
    params: tuple[Parameter, ...]
    body: Region


def literal(node_id: str, value: int | float | bool) -> LiteralExpr:
    return LiteralExpr(node_id=NodeId(node_id), value=value)


def ref(node_id: str, symbol_id: str, name: str) -> Ref:
    return Ref(node_id=NodeId(node_id), symbol_id=SymbolId(symbol_id), name=name)


def param(node_id: str, symbol_id: str, name: str, *, kind: str, dtype: str) -> Parameter:
    return Parameter(
        node_id=NodeId(node_id), symbol_id=SymbolId(symbol_id), name=name, kind=kind, dtype=dtype
    )


def let(node_id: str, symbol_id: str, name: str, value: Expr) -> Let:
    return Let(node_id=NodeId(node_id), symbol_id=SymbolId(symbol_id), name=name, value=value)


def region(region_id: str, *statements: Stmt, node_id: str | None = None) -> Region:
    return Region(
        node_id=NodeId(node_id or f"{region_id}:node"),
        region_id=RegionId(region_id),
        statements=tuple(statements),
    )


def kernel(
    item_id: str, name: str, *, params: tuple[Parameter, ...], body: Region, node_id: str | None = None
) -> Kernel:
    return Kernel(
        node_id=NodeId(node_id or f"{item_id}:node"),
        item_id=ItemId(item_id),
        name=name,
        params=params,
        body=body,
    )


def to_payload(node: Node | tuple[Node, ...]) -> Any:
    if isinstance(node, tuple):
        return [to_payload(item) for item in node]
    if isinstance(node, Kernel):
        return {
            "kind": "Kernel",
            "node_id": node.node_id.to_payload(),
            "item_id": node.item_id.to_payload(),
            "name": node.name,
            "params": [to_payload(item) for item in node.params],
            "body": to_payload(node.body),
        }
    if isinstance(node, Region):
        return {
            "kind": "Region",
            "node_id": node.node_id.to_payload(),
            "region_id": node.region_id.to_payload(),
            "statements": [to_payload(item) for item in node.statements],
        }
    if isinstance(node, Parameter):
        return {
            "kind": "Parameter",
            "node_id": node.node_id.to_payload(),
            "symbol_id": node.symbol_id.to_payload(),
            "name": node.name,
            "dtype": node.dtype,
            "kind_name": node.kind,
        }
    if isinstance(node, Ref):
        return {
            "kind": "Ref",
            "node_id": node.node_id.to_payload(),
            "symbol_id": node.symbol_id.to_payload(),
            "name": node.name,
        }
    if isinstance(node, LiteralExpr):
        return {
            "kind": "LiteralExpr",
            "node_id": node.node_id.to_payload(),
            "value": node.value,
        }
    if isinstance(node, BinaryExpr):
        return {
            "kind": "BinaryExpr",
            "node_id": node.node_id.to_payload(),
            "op": node.op,
            "lhs": to_payload(node.lhs),
            "rhs": to_payload(node.rhs),
        }
    if isinstance(node, Let):
        return {
            "kind": "Let",
            "node_id": node.node_id.to_payload(),
            "symbol_id": node.symbol_id.to_payload(),
            "name": node.name,
            "value": to_payload(node.value),
        }
    if isinstance(node, Return):
        return {
            "kind": "Return",
            "node_id": node.node_id.to_payload(),
            "value": to_payload(node.value),
        }
    raise TypeError(f"Unsupported IR node: {type(node)!r}")


def from_payload(payload: dict[str, Any]) -> Node:
    kind = payload["kind"]
    if kind == "Kernel":
        return Kernel(
            node_id=NodeId(str(payload["node_id"])),
            item_id=ItemId(str(payload["item_id"])),
            name=str(payload["name"]),
            params=tuple(from_payload(item) for item in payload.get("params", ())),  # type: ignore[arg-type]
            body=from_payload(dict(payload["body"])),  # type: ignore[arg-type]
        )
    if kind == "Region":
        return Region(
            node_id=NodeId(str(payload["node_id"])),
            region_id=RegionId(str(payload["region_id"])),
            statements=tuple(from_payload(item) for item in payload.get("statements", ())),  # type: ignore[arg-type]
        )
    if kind == "Parameter":
        return Parameter(
            node_id=NodeId(str(payload["node_id"])),
            symbol_id=SymbolId(str(payload["symbol_id"])),
            name=str(payload["name"]),
            kind=str(payload["kind_name"]),
            dtype=str(payload["dtype"]),
        )
    if kind == "Ref":
        return Ref(
            node_id=NodeId(str(payload["node_id"])),
            symbol_id=SymbolId(str(payload["symbol_id"])),
            name=str(payload["name"]),
        )
    if kind == "LiteralExpr":
        return LiteralExpr(node_id=NodeId(str(payload["node_id"])), value=payload["value"])
    if kind == "BinaryExpr":
        return BinaryExpr(
            node_id=NodeId(str(payload["node_id"])),
            op=str(payload["op"]),  # type: ignore[arg-type]
            lhs=from_payload(dict(payload["lhs"])),  # type: ignore[arg-type]
            rhs=from_payload(dict(payload["rhs"])),  # type: ignore[arg-type]
        )
    if kind == "Let":
        return Let(
            node_id=NodeId(str(payload["node_id"])),
            symbol_id=SymbolId(str(payload["symbol_id"])),
            name=str(payload["name"]),
            value=from_payload(dict(payload["value"])),  # type: ignore[arg-type]
        )
    if kind == "Return":
        return Return(
            node_id=NodeId(str(payload["node_id"])),
            value=from_payload(dict(payload["value"])),  # type: ignore[arg-type]
        )
    raise ValueError(f"Unsupported IR node kind: {kind}")


__all__ = [
    "BinaryExpr",
    "Expr",
    "Item",
    "ItemId",
    "Kernel",
    "Let",
    "LiteralExpr",
    "Node",
    "NodeId",
    "Parameter",
    "Ref",
    "Region",
    "RegionId",
    "Return",
    "Stmt",
    "SymbolId",
    "from_payload",
    "kernel",
    "let",
    "literal",
    "param",
    "ref",
    "region",
    "to_payload",
]
