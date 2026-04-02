from __future__ import annotations

from typing import Any

from .model import (
    BinaryExpr,
    BindingId,
    BindingRef,
    Channel,
    ChannelId,
    Dependency,
    ForStmt,
    ItemId,
    ItemRef,
    Kernel,
    Let,
    LiteralExpr,
    Node,
    NodeId,
    Parameter,
    Process,
    ProcessGraph,
    ProcessId,
    ProcessStep,
    ReceiveExpr,
    Ref,
    Region,
    RegionId,
    Return,
    ScopeId,
    SendStmt,
    SymbolId,
    Task,
    TaskGraph,
    TaskId,
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
        payload = {
            "kind": "TaskGraph",
            "node_id": node.node_id.to_payload(),
            "item_id": node.item_id.to_payload(),
            "name": node.name,
            "tasks": [to_payload(item) for item in node.tasks],
            "dependencies": [to_payload(item) for item in node.dependencies],
        }
        if node.body is not None:
            payload["body"] = to_payload(node.body)
        return payload
    if isinstance(node, ProcessGraph):
        payload = {
            "kind": "ProcessGraph",
            "node_id": node.node_id.to_payload(),
            "item_id": node.item_id.to_payload(),
            "name": node.name,
            "channels": [to_payload(item) for item in node.channels],
            "processes": [to_payload(item) for item in node.processes],
        }
        if node.body is not None:
            payload["body"] = to_payload(node.body)
        return payload
    if isinstance(node, Region):
        payload = {
            "kind": "Region",
            "node_id": node.node_id.to_payload(),
            "region_id": node.region_id.to_payload(),
            "statements": [to_payload(item) for item in node.statements],
        }
        if node.scope_id is not None:
            payload["scope_id"] = node.scope_id.to_payload()
        return payload
    if isinstance(node, Parameter):
        return {
            "kind": "Parameter",
            "node_id": node.node_id.to_payload(),
            "symbol_id": node.symbol_id.to_payload(),
            "name": node.name,
            "dtype": node.dtype,
            "kind_name": node.kind,
        }
    if isinstance(node, BindingRef):
        return {
            "kind": "BindingRef",
            "node_id": node.node_id.to_payload(),
            "binding_id": node.binding_id.to_payload(),
            "name": node.name,
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
        return {"kind": "LiteralExpr", "node_id": node.node_id.to_payload(), "value": node.value}
    if isinstance(node, BinaryExpr):
        return {
            "kind": "BinaryExpr",
            "node_id": node.node_id.to_payload(),
            "op": node.op,
            "lhs": to_payload(node.lhs),
            "rhs": to_payload(node.rhs),
        }
    if isinstance(node, ReceiveExpr):
        return {
            "kind": "ReceiveExpr",
            "node_id": node.node_id.to_payload(),
            "channel_id": node.channel_id.to_payload(),
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
        return {"kind": "Return", "node_id": node.node_id.to_payload(), "value": to_payload(node.value)}
    if isinstance(node, ForStmt):
        return {
            "kind": "ForStmt",
            "node_id": node.node_id.to_payload(),
            "binding_id": node.binding_id.to_payload(),
            "index_name": node.index_name,
            "start": to_payload(node.start),
            "stop": to_payload(node.stop),
            "step": to_payload(node.step),
            "body": to_payload(node.body),
        }
    if isinstance(node, SendStmt):
        return {
            "kind": "SendStmt",
            "node_id": node.node_id.to_payload(),
            "channel_id": node.channel_id.to_payload(),
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
            body=None if payload.get("body") is None else from_payload(dict(payload["body"])),  # type: ignore[arg-type]
        )
    if kind == "ProcessGraph":
        return ProcessGraph(
            node_id=NodeId(str(payload["node_id"])),
            item_id=ItemId(str(payload["item_id"])),
            name=str(payload["name"]),
            channels=tuple(from_payload(item) for item in payload.get("channels", ())),  # type: ignore[arg-type]
            processes=tuple(from_payload(item) for item in payload.get("processes", ())),  # type: ignore[arg-type]
            body=None if payload.get("body") is None else from_payload(dict(payload["body"])),  # type: ignore[arg-type]
        )
    if kind == "Region":
        return Region(
            node_id=NodeId(str(payload["node_id"])),
            region_id=RegionId(str(payload["region_id"])),
            statements=tuple(from_payload(item) for item in payload.get("statements", ())),  # type: ignore[arg-type]
            scope_id=None if payload.get("scope_id") is None else ScopeId(str(payload["scope_id"])),
        )
    if kind == "Parameter":
        return Parameter(
            node_id=NodeId(str(payload["node_id"])),
            symbol_id=SymbolId(str(payload["symbol_id"])),
            name=str(payload["name"]),
            kind=str(payload["kind_name"]),
            dtype=str(payload["dtype"]),
        )
    if kind == "BindingRef":
        return BindingRef(
            node_id=NodeId(str(payload["node_id"])),
            binding_id=BindingId(str(payload["binding_id"])),
            name=str(payload["name"]),
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
    if kind == "ReceiveExpr":
        return ReceiveExpr(
            node_id=NodeId(str(payload["node_id"])),
            channel_id=ChannelId(str(payload["channel_id"])),
        )
    if kind == "Let":
        return Let(
            node_id=NodeId(str(payload["node_id"])),
            symbol_id=SymbolId(str(payload["symbol_id"])),
            name=str(payload["name"]),
            value=from_payload(dict(payload["value"])),  # type: ignore[arg-type]
        )
    if kind == "Return":
        return Return(node_id=NodeId(str(payload["node_id"])), value=from_payload(dict(payload["value"])))  # type: ignore[arg-type]
    if kind == "ForStmt":
        return ForStmt(
            node_id=NodeId(str(payload["node_id"])),
            binding_id=BindingId(str(payload["binding_id"])),
            index_name=str(payload["index_name"]),
            start=from_payload(dict(payload["start"])),  # type: ignore[arg-type]
            stop=from_payload(dict(payload["stop"])),  # type: ignore[arg-type]
            step=from_payload(dict(payload["step"])),  # type: ignore[arg-type]
            body=from_payload(dict(payload["body"])),  # type: ignore[arg-type]
        )
    if kind == "SendStmt":
        return SendStmt(
            node_id=NodeId(str(payload["node_id"])),
            channel_id=ChannelId(str(payload["channel_id"])),
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


__all__ = ["from_payload", "to_payload"]
