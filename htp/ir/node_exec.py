"""Interpreter registration façade for typed IR node execution."""

from __future__ import annotations

from .interpreter import register_interpreter
from .node_interpreters import (
    KernelInterpreter,
    KernelModuleInterpreter,
    NodeProgramInterpreter,
    ProcessGraphInterpreter,
    ProcessGraphModuleInterpreter,
    TaskGraphInterpreter,
    TaskGraphModuleInterpreter,
)
from .node_runtime import ExecutionEnv, ExprEvaluator, StmtExecutor

NODE_PROGRAM_INTERPRETER_ID = "htp.interpreter.program_nodes.v1"
NODE_KERNEL_INTERPRETER_ID = "htp.interpreter.kernel_nodes.v1"
NODE_TASK_GRAPH_INTERPRETER_ID = "htp.interpreter.task_graph_nodes.v1"
NODE_PROCESS_GRAPH_INTERPRETER_ID = "htp.interpreter.process_graph_nodes.v1"


KERNEL_MODULE_INTERPRETER = KernelModuleInterpreter()
TASK_GRAPH_MODULE_INTERPRETER = TaskGraphModuleInterpreter()
PROCESS_GRAPH_MODULE_INTERPRETER = ProcessGraphModuleInterpreter()
NODE_PROGRAM_INTERPRETER = NodeProgramInterpreter()


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
