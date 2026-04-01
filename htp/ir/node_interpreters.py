"""Typed IR interpreter units separated from registration and constants."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from .module import ProgramModule
from .node_runtime import ExecutionEnv, ExprEvaluator, ReturnSignal, StmtExecutor
from .nodes import Channel, Dependency, Kernel, Process, ProcessGraph, ProcessStep, Task, TaskGraph


@dataclass
class KernelInterpreter:
    """Execute one typed ``Kernel`` item."""

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
        except ReturnSignal as signal:
            return signal.value
        return None


class TaskGraphInterpreter:
    """Execute/report one typed ``TaskGraph`` item."""

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
    """Execute/report one typed ``ProcessGraph`` item."""

    def run(self, graph: ProcessGraph) -> dict[str, Any]:
        return {
            "graph": graph.name,
            "channels": [_channel_payload(channel) for channel in graph.channels],
            "processes": [_process_payload(process) for process in graph.processes],
        }


@dataclass
class KernelModuleInterpreter:
    """Run the first typed kernel item in a ``ProgramModule``."""

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
        kernel = find_typed_item(module, Kernel)
        return self.kernel_interpreter.run(kernel, args=args, kwargs=kwargs)


@dataclass
class TaskGraphModuleInterpreter:
    """Run/report the first typed task graph in a ``ProgramModule``."""

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
        graph = find_typed_item(module, TaskGraph)
        return {"entry": entry, **self.task_graph_interpreter.run(graph)}


@dataclass
class ProcessGraphModuleInterpreter:
    """Run/report the first typed process graph in a ``ProgramModule``."""

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
        graph = find_typed_item(module, ProcessGraph)
        return {"entry": entry, **self.process_graph_interpreter.run(graph)}


@dataclass
class NodeProgramInterpreter:
    """Dispatch one ``ProgramModule`` through object-owned typed interpreters."""

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
        report: dict[str, Any] = {"ok": True, "entry": entry, "interpreter_units": {}}
        if any(isinstance(item, Kernel) for item in module.items.typed_items):
            kernel = find_typed_item(module, Kernel)
            report["interpreter_units"]["kernel"] = type(self.kernel).__name__
            report["kernel"] = {
                "name": kernel.name,
                "arg_count": len(kernel.params),
                "provided_args": len(args) + len(kwargs),
            }
        if any(isinstance(item, TaskGraph) for item in module.items.typed_items):
            graph = find_typed_item(module, TaskGraph)
            report["interpreter_units"]["task_graph"] = type(self.task_graph).__name__
            report["task_graph"] = self.task_graph.run(graph)
        if any(isinstance(item, ProcessGraph) for item in module.items.typed_items):
            graph = find_typed_item(module, ProcessGraph)
            report["interpreter_units"]["process_graph"] = type(self.process_graph).__name__
            report["process_graph"] = self.process_graph.run(graph)
        return report


def find_typed_item(module: ProgramModule, expected_type: type[Any]) -> Any:
    """Find one typed item of the requested kind inside a ``ProgramModule``."""

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


__all__ = [
    "KernelInterpreter",
    "KernelModuleInterpreter",
    "NodeProgramInterpreter",
    "ProcessGraphInterpreter",
    "ProcessGraphModuleInterpreter",
    "TaskGraphInterpreter",
    "TaskGraphModuleInterpreter",
    "find_typed_item",
]
