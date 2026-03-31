from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .interpreter import register_interpreter
from .module import ProgramModule
from .nodes import (
    BinaryExpr,
    Channel,
    Dependency,
    Kernel,
    Let,
    LiteralExpr,
    Process,
    ProcessGraph,
    ProcessStep,
    Ref,
    Region,
    Return,
    Task,
    TaskGraph,
)

NODE_KERNEL_INTERPRETER_ID = "htp.interpreter.kernel_nodes.v1"
NODE_TASK_GRAPH_INTERPRETER_ID = "htp.interpreter.task_graph_nodes.v1"
NODE_PROCESS_GRAPH_INTERPRETER_ID = "htp.interpreter.process_graph_nodes.v1"


class _ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        super().__init__("kernel_return")
        self.value = value


@dataclass
class _ExecutionContext:
    env: dict[str, Any]


def run_kernel_module(
    module: ProgramModule,
    *,
    entry: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    mode: str,
    runtime: Any | None,
    trace: Any | None,
) -> Any:
    del entry, mode, runtime, trace
    typed_items = module.items.typed_items
    if not typed_items:
        raise ValueError("ProgramModule has no typed_items payload for kernel-node execution")
    kernels = [item for item in typed_items if isinstance(item, Kernel)]
    if not kernels:
        raise ValueError("ProgramModule typed_items payload does not contain a Kernel item")
    return _run_kernel(kernels[0], args=args, kwargs=kwargs)


def run_task_graph_module(
    module: ProgramModule,
    *,
    entry: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    mode: str,
    runtime: Any | None,
    trace: Any | None,
) -> dict[str, Any]:
    del args, kwargs, mode, runtime, trace
    graph = _find_item(module, TaskGraph)
    ordered_tasks = _topological_task_order(graph.tasks, graph.dependencies)
    return {
        "entry": entry,
        "graph": graph.name,
        "tasks": [
            {
                "task_id": task.task_id.value,
                "kernel": task.kernel.name,
                "args": [arg.name for arg in task.args],
                "attrs": dict(task.attrs),
            }
            for task in ordered_tasks
        ],
        "dependencies": [
            {"src": dependency.src_task.value, "dst": dependency.dst_task.value}
            for dependency in graph.dependencies
        ],
    }


def run_process_graph_module(
    module: ProgramModule,
    *,
    entry: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    mode: str,
    runtime: Any | None,
    trace: Any | None,
) -> dict[str, Any]:
    del args, kwargs, mode, runtime, trace
    graph = _find_item(module, ProcessGraph)
    return {
        "entry": entry,
        "graph": graph.name,
        "channels": [_channel_payload(channel) for channel in graph.channels],
        "processes": [_process_payload(process) for process in graph.processes],
    }


def _find_item(module: ProgramModule, expected_type: type[Any]) -> Any:
    for item in module.items.typed_items:
        if isinstance(item, expected_type):
            return item
    raise ValueError(f"ProgramModule typed_items payload does not contain {expected_type.__name__}")


def _run_kernel(kernel: Kernel, *, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    env: dict[str, Any] = {}
    for parameter, value in zip(kernel.params, args, strict=False):
        env[parameter.symbol_id.value] = value
    for parameter in kernel.params[len(args) :]:
        if parameter.name in kwargs:
            env[parameter.symbol_id.value] = kwargs[parameter.name]
        else:
            raise KeyError(f"Missing kernel argument: {parameter.name}")
    context = _ExecutionContext(env=env)
    try:
        _exec_region(kernel.body, context)
    except _ReturnSignal as signal:
        return signal.value
    return None


def _exec_region(region: Region, context: _ExecutionContext) -> None:
    for statement in region.statements:
        _exec_stmt(statement, context)


def _exec_stmt(statement: Any, context: _ExecutionContext) -> None:
    if isinstance(statement, Let):
        context.env[statement.symbol_id.value] = _eval_expr(statement.value, context)
        return
    if isinstance(statement, Return):
        raise _ReturnSignal(_eval_expr(statement.value, context))
    raise TypeError(f"Unsupported kernel-node statement: {type(statement)!r}")


def _eval_expr(expr: Any, context: _ExecutionContext) -> Any:
    if isinstance(expr, Ref):
        return context.env[expr.symbol_id.value]
    if isinstance(expr, LiteralExpr):
        return expr.value
    if isinstance(expr, BinaryExpr):
        lhs = _eval_expr(expr.lhs, context)
        rhs = _eval_expr(expr.rhs, context)
        if expr.op == "add":
            return lhs + rhs
        if expr.op == "sub":
            return lhs - rhs
        if expr.op == "mul":
            return lhs * rhs
        if expr.op == "div":
            return lhs / rhs
        raise ValueError(f"Unsupported binary op: {expr.op}")
    raise TypeError(f"Unsupported kernel-node expression: {type(expr)!r}")


def _topological_task_order(
    tasks: tuple[Task, ...], dependencies: tuple[Dependency, ...]
) -> tuple[Task, ...]:
    tasks_by_id = {task.task_id.value: task for task in tasks}
    indegree: dict[str, int] = {task_id: 0 for task_id in tasks_by_id}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for dependency in dependencies:
        src = dependency.src_task.value
        dst = dependency.dst_task.value
        outgoing[src].append(dst)
        indegree[dst] = indegree.get(dst, 0) + 1
    ready = deque(task_id for task_id, degree in indegree.items() if degree == 0)
    ordered: list[Task] = []
    while ready:
        task_id = ready.popleft()
        ordered.append(tasks_by_id[task_id])
        for successor in outgoing.get(task_id, ()):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    if len(ordered) != len(tasks):
        raise ValueError("TaskGraph dependencies contain a cycle")
    return tuple(ordered)


def _channel_payload(channel: Channel) -> dict[str, Any]:
    return {
        "channel_id": channel.channel_id.value,
        "name": channel.name,
        "dtype": channel.dtype,
        "capacity": channel.capacity,
        "protocol": channel.protocol,
    }


def _process_payload(process: Process) -> dict[str, Any]:
    return {
        "process_id": process.process_id.value,
        "kernel": process.kernel.name,
        "args": [arg.name for arg in process.args],
        "attrs": dict(process.attrs),
        "steps": [_process_step_payload(step) for step in process.steps],
    }


def _process_step_payload(step: ProcessStep) -> dict[str, Any]:
    payload = {"kind": step.kind, "attrs": dict(step.attrs)}
    if step.channel_id is not None:
        payload["channel_id"] = step.channel_id.value
    return payload


register_interpreter(NODE_KERNEL_INTERPRETER_ID, run_kernel_module)
register_interpreter(NODE_TASK_GRAPH_INTERPRETER_ID, run_task_graph_module)
register_interpreter(NODE_PROCESS_GRAPH_INTERPRETER_ID, run_process_graph_module)


__all__ = [
    "NODE_KERNEL_INTERPRETER_ID",
    "NODE_PROCESS_GRAPH_INTERPRETER_ID",
    "NODE_TASK_GRAPH_INTERPRETER_ID",
    "run_kernel_module",
    "run_process_graph_module",
    "run_task_graph_module",
]
