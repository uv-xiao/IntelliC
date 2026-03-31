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


def literal(node_id: str, value: int | float | bool) -> LiteralExpr:
    return LiteralExpr(node_id=NodeId(node_id), value=value)


def ref(node_id: str, symbol_id: str, name: str) -> Ref:
    return Ref(node_id=NodeId(node_id), symbol_id=SymbolId(symbol_id), name=name)


def item_ref(node_id: str, item_id: str, name: str) -> ItemRef:
    return ItemRef(node_id=NodeId(node_id), item_id=ItemId(item_id), name=name)


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
    item_id: str,
    name: str,
    *,
    params: tuple[Parameter, ...],
    body: Region,
    node_id: str | None = None,
) -> Kernel:
    return Kernel(
        node_id=NodeId(node_id or f"{item_id}:node"),
        item_id=ItemId(item_id),
        name=name,
        params=params,
        body=body,
    )


def task(
    node_id: str,
    task_id: str,
    *,
    kernel: ItemRef,
    args: tuple[Ref, ...] = (),
    attrs: dict[str, Any] | None = None,
) -> Task:
    return Task(
        node_id=NodeId(node_id),
        task_id=TaskId(task_id),
        kernel=kernel,
        args=args,
        attrs={} if attrs is None else dict(attrs),
    )


def dependency(node_id: str, *, src_task: str, dst_task: str) -> Dependency:
    return Dependency(node_id=NodeId(node_id), src_task=TaskId(src_task), dst_task=TaskId(dst_task))


def task_graph(
    item_id: str,
    name: str,
    *,
    tasks: tuple[Task, ...],
    dependencies: tuple[Dependency, ...] = (),
    node_id: str | None = None,
) -> TaskGraph:
    return TaskGraph(
        node_id=NodeId(node_id or f"{item_id}:node"),
        item_id=ItemId(item_id),
        name=name,
        tasks=tasks,
        dependencies=dependencies,
    )


def channel(
    item_id: str,
    name: str,
    *,
    channel_id: str,
    dtype: str,
    capacity: int,
    protocol: str = "fifo",
    node_id: str | None = None,
) -> Channel:
    return Channel(
        node_id=NodeId(node_id or f"{item_id}:node"),
        item_id=ItemId(item_id),
        name=name,
        channel_id=ChannelId(channel_id),
        dtype=dtype,
        capacity=capacity,
        protocol=protocol,
    )


def process_step(
    node_id: str,
    *,
    kind: str,
    channel_id: str | None = None,
    attrs: dict[str, Any] | None = None,
) -> ProcessStep:
    return ProcessStep(
        node_id=NodeId(node_id),
        kind=kind,
        channel_id=None if channel_id is None else ChannelId(channel_id),
        attrs={} if attrs is None else dict(attrs),
    )


def process(
    node_id: str,
    process_id: str,
    *,
    kernel: ItemRef,
    args: tuple[Ref, ...] = (),
    steps: tuple[ProcessStep, ...] = (),
    attrs: dict[str, Any] | None = None,
) -> Process:
    return Process(
        node_id=NodeId(node_id),
        process_id=ProcessId(process_id),
        kernel=kernel,
        args=args,
        steps=steps,
        attrs={} if attrs is None else dict(attrs),
    )


def process_graph(
    item_id: str,
    name: str,
    *,
    channels: tuple[Channel, ...],
    processes: tuple[Process, ...],
    node_id: str | None = None,
) -> ProcessGraph:
    return ProcessGraph(
        node_id=NodeId(node_id or f"{item_id}:node"),
        item_id=ItemId(item_id),
        name=name,
        channels=channels,
        processes=processes,
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
    if isinstance(node, TaskGraph):
        return {
            "kind": "TaskGraph",
            "node_id": node.node_id.to_payload(),
            "item_id": node.item_id.to_payload(),
            "name": node.name,
            "tasks": [to_payload(item) for item in node.tasks],
            "dependencies": [to_payload(item) for item in node.dependencies],
        }
    if isinstance(node, ProcessGraph):
        return {
            "kind": "ProcessGraph",
            "node_id": node.node_id.to_payload(),
            "item_id": node.item_id.to_payload(),
            "name": node.name,
            "channels": [to_payload(item) for item in node.channels],
            "processes": [to_payload(item) for item in node.processes],
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
    if isinstance(node, ItemRef):
        return {
            "kind": "ItemRef",
            "node_id": node.node_id.to_payload(),
            "item_id": node.item_id.to_payload(),
            "name": node.name,
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
    if isinstance(node, Task):
        return {
            "kind": "Task",
            "node_id": node.node_id.to_payload(),
            "task_id": node.task_id.to_payload(),
            "kernel": to_payload(node.kernel),
            "args": [to_payload(item) for item in node.args],
            "attrs": dict(node.attrs),
        }
    if isinstance(node, Dependency):
        return {
            "kind": "Dependency",
            "node_id": node.node_id.to_payload(),
            "src_task": node.src_task.to_payload(),
            "dst_task": node.dst_task.to_payload(),
        }
    if isinstance(node, Channel):
        return {
            "kind": "Channel",
            "node_id": node.node_id.to_payload(),
            "item_id": node.item_id.to_payload(),
            "name": node.name,
            "channel_id": node.channel_id.to_payload(),
            "dtype": node.dtype,
            "capacity": node.capacity,
            "protocol": node.protocol,
        }
    if isinstance(node, ProcessStep):
        return {
            "kind": "ProcessStep",
            "node_id": node.node_id.to_payload(),
            "step_kind": node.kind,
            "channel_id": None if node.channel_id is None else node.channel_id.to_payload(),
            "attrs": dict(node.attrs),
        }
    if isinstance(node, Process):
        return {
            "kind": "Process",
            "node_id": node.node_id.to_payload(),
            "process_id": node.process_id.to_payload(),
            "kernel": to_payload(node.kernel),
            "args": [to_payload(item) for item in node.args],
            "steps": [to_payload(item) for item in node.steps],
            "attrs": dict(node.attrs),
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
    if kind == "TaskGraph":
        return TaskGraph(
            node_id=NodeId(str(payload["node_id"])),
            item_id=ItemId(str(payload["item_id"])),
            name=str(payload["name"]),
            tasks=tuple(from_payload(item) for item in payload.get("tasks", ())),  # type: ignore[arg-type]
            dependencies=tuple(from_payload(item) for item in payload.get("dependencies", ())),  # type: ignore[arg-type]
        )
    if kind == "ProcessGraph":
        return ProcessGraph(
            node_id=NodeId(str(payload["node_id"])),
            item_id=ItemId(str(payload["item_id"])),
            name=str(payload["name"]),
            channels=tuple(from_payload(item) for item in payload.get("channels", ())),  # type: ignore[arg-type]
            processes=tuple(from_payload(item) for item in payload.get("processes", ())),  # type: ignore[arg-type]
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
    if kind == "ItemRef":
        return ItemRef(
            node_id=NodeId(str(payload["node_id"])),
            item_id=ItemId(str(payload["item_id"])),
            name=str(payload["name"]),
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
    if kind == "Task":
        return Task(
            node_id=NodeId(str(payload["node_id"])),
            task_id=TaskId(str(payload["task_id"])),
            kernel=from_payload(dict(payload["kernel"])),  # type: ignore[arg-type]
            args=tuple(from_payload(item) for item in payload.get("args", ())),  # type: ignore[arg-type]
            attrs=dict(payload.get("attrs", {})),
        )
    if kind == "Dependency":
        return Dependency(
            node_id=NodeId(str(payload["node_id"])),
            src_task=TaskId(str(payload["src_task"])),
            dst_task=TaskId(str(payload["dst_task"])),
        )
    if kind == "Channel":
        return Channel(
            node_id=NodeId(str(payload["node_id"])),
            item_id=ItemId(str(payload["item_id"])),
            name=str(payload["name"]),
            channel_id=ChannelId(str(payload["channel_id"])),
            dtype=str(payload["dtype"]),
            capacity=int(payload["capacity"]),
            protocol=str(payload.get("protocol", "fifo")),
        )
    if kind == "ProcessStep":
        channel_id = payload.get("channel_id")
        return ProcessStep(
            node_id=NodeId(str(payload["node_id"])),
            kind=str(payload["step_kind"]),
            channel_id=None if channel_id is None else ChannelId(str(channel_id)),
            attrs=dict(payload.get("attrs", {})),
        )
    if kind == "Process":
        return Process(
            node_id=NodeId(str(payload["node_id"])),
            process_id=ProcessId(str(payload["process_id"])),
            kernel=from_payload(dict(payload["kernel"])),  # type: ignore[arg-type]
            args=tuple(from_payload(item) for item in payload.get("args", ())),  # type: ignore[arg-type]
            steps=tuple(from_payload(item) for item in payload.get("steps", ())),  # type: ignore[arg-type]
            attrs=dict(payload.get("attrs", {})),
        )
    raise ValueError(f"Unsupported IR node kind: {kind}")


__all__ = [
    "BinaryExpr",
    "Channel",
    "ChannelId",
    "Dependency",
    "Expr",
    "Item",
    "ItemId",
    "ItemRef",
    "Kernel",
    "Let",
    "LiteralExpr",
    "Node",
    "NodeId",
    "Parameter",
    "Process",
    "ProcessGraph",
    "ProcessId",
    "ProcessStep",
    "Ref",
    "Region",
    "RegionId",
    "Return",
    "Stmt",
    "SymbolId",
    "Task",
    "TaskGraph",
    "TaskId",
    "channel",
    "dependency",
    "from_payload",
    "item_ref",
    "kernel",
    "let",
    "literal",
    "param",
    "process",
    "process_graph",
    "process_step",
    "ref",
    "region",
    "task",
    "task_graph",
    "to_payload",
]
