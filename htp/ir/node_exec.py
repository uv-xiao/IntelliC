from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from .interpreter import register_interpreter
from .module import ProgramModule
from .nodes import (
    BinaryExpr,
    BindingRef,
    Channel,
    Dependency,
    ForStmt,
    Kernel,
    Let,
    LiteralExpr,
    Process,
    ProcessGraph,
    ProcessStep,
    ReceiveExpr,
    Ref,
    Region,
    Return,
    SendStmt,
    Task,
    TaskGraph,
)

NODE_PROGRAM_INTERPRETER_ID = "htp.interpreter.program_nodes.v1"
NODE_KERNEL_INTERPRETER_ID = "htp.interpreter.kernel_nodes.v1"
NODE_TASK_GRAPH_INTERPRETER_ID = "htp.interpreter.task_graph_nodes.v1"
NODE_PROCESS_GRAPH_INTERPRETER_ID = "htp.interpreter.process_graph_nodes.v1"


class _ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        super().__init__("kernel_return")
        self.value = value


@dataclass
class ExecutionEnv:
    env: dict[str, Any] = field(default_factory=dict)
    channels: dict[str, list[Any]] = field(default_factory=lambda: defaultdict(list))


class ExprEvaluator:
    def eval(self, expr: Any, env: ExecutionEnv) -> Any:
        if isinstance(expr, Ref):
            return env.env[expr.symbol_id.value]
        if isinstance(expr, BindingRef):
            return env.env[expr.binding_id.value]
        if isinstance(expr, LiteralExpr):
            return expr.value
        if isinstance(expr, ReceiveExpr):
            queue = env.channels.setdefault(expr.channel_id.value, [])
            if queue:
                return queue.pop(0)
            return {"channel_id": expr.channel_id.value, "received": True}
        if isinstance(expr, BinaryExpr):
            lhs = self.eval(expr.lhs, env)
            rhs = self.eval(expr.rhs, env)
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


@dataclass
class StmtExecutor:
    expr_evaluator: ExprEvaluator

    def exec(self, statement: Any, env: ExecutionEnv) -> None:
        if isinstance(statement, Let):
            env.env[statement.symbol_id.value] = self.expr_evaluator.eval(statement.value, env)
            return
        if isinstance(statement, Return):
            raise _ReturnSignal(self.expr_evaluator.eval(statement.value, env))
        if isinstance(statement, ForStmt):
            self._exec_for(statement, env)
            return
        if isinstance(statement, SendStmt):
            value = self.expr_evaluator.eval(statement.value, env)
            env.channels.setdefault(statement.channel_id.value, []).append(value)
            return
        raise TypeError(f"Unsupported kernel-node statement: {type(statement)!r}")

    def _exec_for(self, statement: ForStmt, env: ExecutionEnv) -> None:
        start = int(self.expr_evaluator.eval(statement.start, env))
        stop = int(self.expr_evaluator.eval(statement.stop, env))
        step = int(self.expr_evaluator.eval(statement.step, env))
        for value in range(start, stop, step):
            env.env[statement.binding_id.value] = value
            self.exec_region(statement.body, env)

    def exec_region(self, region: Region, env: ExecutionEnv) -> None:
        for statement in region.statements:
            self.exec(statement, env)


@dataclass
class KernelInterpreter:
    expr_evaluator: ExprEvaluator = field(default_factory=ExprEvaluator)
    stmt_executor: StmtExecutor = field(init=False)

    def __post_init__(self) -> None:
        self.stmt_executor = StmtExecutor(expr_evaluator=self.expr_evaluator)

    def run(self, kernel: Kernel, *, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        env = ExecutionEnv()
        for parameter, value in zip(kernel.params, args, strict=False):
            env.env[parameter.symbol_id.value] = value
        for parameter in kernel.params[len(args) :]:
            if parameter.name in kwargs:
                env.env[parameter.symbol_id.value] = kwargs[parameter.name]
            elif parameter.kind not in {"shape", "buffer"}:
                raise KeyError(f"Missing kernel argument: {parameter.name}")
            else:
                env.env[parameter.symbol_id.value] = {
                    "parameter": parameter.name,
                    "kind": parameter.kind,
                }
        try:
            self.stmt_executor.exec_region(kernel.body, env)
        except _ReturnSignal as signal:
            return signal.value
        return None


class TaskGraphInterpreter:
    def run(self, graph: TaskGraph) -> dict[str, Any]:
        ordered_tasks = _topological_task_order(graph.tasks, graph.dependencies)
        return {
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


class ProcessGraphInterpreter:
    def run(self, graph: ProcessGraph) -> dict[str, Any]:
        return {
            "graph": graph.name,
            "channels": [_channel_payload(channel) for channel in graph.channels],
            "processes": [_process_payload(process) for process in graph.processes],
        }


@dataclass
class KernelModuleInterpreter:
    kernel_interpreter: KernelInterpreter = field(default_factory=KernelInterpreter)

    def run(
        self,
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
        kernel = _find_item(module, Kernel)
        return self.kernel_interpreter.run(kernel, args=args, kwargs=kwargs)


@dataclass
class TaskGraphModuleInterpreter:
    task_graph_interpreter: TaskGraphInterpreter = field(default_factory=TaskGraphInterpreter)

    def run(
        self,
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
        return {"entry": entry, **self.task_graph_interpreter.run(graph)}


@dataclass
class ProcessGraphModuleInterpreter:
    process_graph_interpreter: ProcessGraphInterpreter = field(default_factory=ProcessGraphInterpreter)

    def run(
        self,
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
        return {"entry": entry, **self.process_graph_interpreter.run(graph)}


@dataclass
class NodeProgramInterpreter:
    kernel: KernelInterpreter = field(default_factory=KernelInterpreter)
    task_graph: TaskGraphInterpreter = field(default_factory=TaskGraphInterpreter)
    process_graph: ProcessGraphInterpreter = field(default_factory=ProcessGraphInterpreter)

    def run(
        self,
        module: ProgramModule,
        *,
        entry: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        mode: str,
        runtime: Any | None,
        trace: Any | None,
    ) -> dict[str, Any]:
        del mode, runtime, trace
        report: dict[str, Any] = {
            "ok": True,
            "entry": entry,
            "interpreter_units": {},
        }
        if any(isinstance(item, Kernel) for item in module.items.typed_items):
            report["interpreter_units"]["kernel"] = type(self.kernel).__name__
            report["kernel"] = {
                "name": _find_item(module, Kernel).name,
                "arg_count": len(_find_item(module, Kernel).params),
                "provided_args": len(args) + len(kwargs),
            }
        if any(isinstance(item, TaskGraph) for item in module.items.typed_items):
            graph = _find_item(module, TaskGraph)
            report["interpreter_units"]["task_graph"] = type(self.task_graph).__name__
            report["task_graph"] = self.task_graph.run(graph)
        if any(isinstance(item, ProcessGraph) for item in module.items.typed_items):
            graph = _find_item(module, ProcessGraph)
            report["interpreter_units"]["process_graph"] = type(self.process_graph).__name__
            report["process_graph"] = self.process_graph.run(graph)
        return report


KERNEL_MODULE_INTERPRETER = KernelModuleInterpreter()
TASK_GRAPH_MODULE_INTERPRETER = TaskGraphModuleInterpreter()
PROCESS_GRAPH_MODULE_INTERPRETER = ProcessGraphModuleInterpreter()
NODE_PROGRAM_INTERPRETER = NodeProgramInterpreter()


def _find_item(module: ProgramModule, expected_type: type[Any]) -> Any:
    for item in module.items.typed_items:
        if isinstance(item, expected_type):
            return item
    raise ValueError(f"ProgramModule typed_items payload does not contain {expected_type.__name__}")


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


register_interpreter(NODE_PROGRAM_INTERPRETER_ID, NODE_PROGRAM_INTERPRETER)
register_interpreter(NODE_KERNEL_INTERPRETER_ID, KERNEL_MODULE_INTERPRETER)
register_interpreter(NODE_TASK_GRAPH_INTERPRETER_ID, TASK_GRAPH_MODULE_INTERPRETER)
register_interpreter(NODE_PROCESS_GRAPH_INTERPRETER_ID, PROCESS_GRAPH_MODULE_INTERPRETER)


__all__ = [
    "ExecutionEnv",
    "ExprEvaluator",
    "KernelInterpreter",
    "NODE_KERNEL_INTERPRETER_ID",
    "NODE_PROCESS_GRAPH_INTERPRETER_ID",
    "NODE_PROGRAM_INTERPRETER_ID",
    "NODE_TASK_GRAPH_INTERPRETER_ID",
    "NodeProgramInterpreter",
    "ProcessGraphInterpreter",
    "StmtExecutor",
    "TaskGraphInterpreter",
]
