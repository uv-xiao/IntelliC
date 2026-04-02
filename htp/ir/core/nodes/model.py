from __future__ import annotations

from dataclasses import dataclass, field
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
class BindingId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class ScopeId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class RegionId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaskId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class ProcessId:
    value: str

    def to_payload(self) -> str:
        return self.value


@dataclass(frozen=True)
class ChannelId:
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
class ItemRef(Node):
    item_id: ItemId
    name: str


@dataclass(frozen=True)
class Parameter(Node):
    symbol_id: SymbolId
    name: str
    kind: str
    dtype: str


@dataclass(frozen=True)
class BindingRef(Expr):
    binding_id: BindingId
    name: str


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
class ReceiveExpr(Expr):
    channel_id: ChannelId


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
    scope_id: ScopeId | None = None


@dataclass(frozen=True)
class ForStmt(Stmt):
    binding_id: BindingId
    index_name: str
    start: Expr
    stop: Expr
    step: Expr
    body: Region


@dataclass(frozen=True)
class SendStmt(Stmt):
    channel_id: ChannelId
    value: Expr


@dataclass(frozen=True)
class Kernel(Item):
    params: tuple[Parameter, ...]
    body: Region


@dataclass(frozen=True)
class Task(Node):
    task_id: TaskId
    kernel: ItemRef
    args: tuple[Ref, ...] = ()
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Dependency(Node):
    src_task: TaskId
    dst_task: TaskId


@dataclass(frozen=True)
class TaskGraph(Item):
    tasks: tuple[Task, ...]
    dependencies: tuple[Dependency, ...] = ()
    body: Region | None = None


@dataclass(frozen=True)
class Channel(Item):
    channel_id: ChannelId
    dtype: str
    capacity: int
    protocol: str = "fifo"


@dataclass(frozen=True)
class ProcessStep(Node):
    kind: str
    channel_id: ChannelId | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Process(Node):
    process_id: ProcessId
    kernel: ItemRef
    args: tuple[Ref, ...] = ()
    steps: tuple[ProcessStep, ...] = ()
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessGraph(Item):
    channels: tuple[Channel, ...]
    processes: tuple[Process, ...]
    body: Region | None = None
