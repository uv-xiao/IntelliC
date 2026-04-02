from __future__ import annotations

from typing import Any

from .model import (
    BindingId,
    BindingRef,
    Channel,
    ChannelId,
    Dependency,
    Expr,
    ForStmt,
    ItemId,
    ItemRef,
    Kernel,
    Let,
    LiteralExpr,
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
    ScopeId,
    SendStmt,
    Stmt,
    SymbolId,
    Task,
    TaskGraph,
    TaskId,
)


def literal(node_id: str, value: int | float | bool) -> LiteralExpr:
    return LiteralExpr(node_id=NodeId(node_id), value=value)


def ref(node_id: str, symbol_id: str, name: str) -> Ref:
    return Ref(node_id=NodeId(node_id), symbol_id=SymbolId(symbol_id), name=name)


def binding_ref(node_id: str, binding_id: str, name: str) -> BindingRef:
    return BindingRef(node_id=NodeId(node_id), binding_id=BindingId(binding_id), name=name)


def item_ref(node_id: str, item_id: str, name: str) -> ItemRef:
    return ItemRef(node_id=NodeId(node_id), item_id=ItemId(item_id), name=name)


def param(node_id: str, symbol_id: str, name: str, *, kind: str, dtype: str) -> Parameter:
    return Parameter(
        node_id=NodeId(node_id), symbol_id=SymbolId(symbol_id), name=name, kind=kind, dtype=dtype
    )


def let(node_id: str, symbol_id: str, name: str, value: Expr) -> Let:
    return Let(node_id=NodeId(node_id), symbol_id=SymbolId(symbol_id), name=name, value=value)


def region(
    region_id: str,
    *statements: Stmt,
    node_id: str | None = None,
    scope_id: str | None = None,
) -> Region:
    return Region(
        node_id=NodeId(node_id or f"{region_id}:node"),
        region_id=RegionId(region_id),
        statements=tuple(statements),
        scope_id=None if scope_id is None else ScopeId(scope_id),
    )


def for_stmt(
    node_id: str,
    binding_id: str,
    index_name: str,
    *,
    start: Expr,
    stop: Expr,
    step: Expr,
    body: Region,
) -> ForStmt:
    return ForStmt(
        node_id=NodeId(node_id),
        binding_id=BindingId(binding_id),
        index_name=index_name,
        start=start,
        stop=stop,
        step=step,
        body=body,
    )


def send_stmt(node_id: str, *, channel_id: str, value: Expr) -> SendStmt:
    return SendStmt(node_id=NodeId(node_id), channel_id=ChannelId(channel_id), value=value)


def receive_expr(node_id: str, *, channel_id: str) -> ReceiveExpr:
    return ReceiveExpr(node_id=NodeId(node_id), channel_id=ChannelId(channel_id))


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
    body: Region | None = None,
    node_id: str | None = None,
) -> TaskGraph:
    return TaskGraph(
        node_id=NodeId(node_id or f"{item_id}:node"),
        item_id=ItemId(item_id),
        name=name,
        tasks=tasks,
        dependencies=dependencies,
        body=body,
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
    body: Region | None = None,
    node_id: str | None = None,
) -> ProcessGraph:
    return ProcessGraph(
        node_id=NodeId(node_id or f"{item_id}:node"),
        item_id=ItemId(item_id),
        name=name,
        channels=channels,
        processes=processes,
        body=body,
    )


__all__ = [
    "binding_ref",
    "channel",
    "dependency",
    "for_stmt",
    "item_ref",
    "kernel",
    "let",
    "literal",
    "param",
    "process",
    "process_graph",
    "process_step",
    "receive_expr",
    "ref",
    "region",
    "send_stmt",
    "task",
    "task_graph",
]
