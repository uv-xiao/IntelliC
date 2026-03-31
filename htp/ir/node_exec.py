from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .interpreter import register_interpreter
from .module import ProgramModule
from .nodes import BinaryExpr, Kernel, Let, LiteralExpr, Ref, Region, Return

NODE_KERNEL_INTERPRETER_ID = "htp.interpreter.kernel_nodes.v1"


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


register_interpreter(NODE_KERNEL_INTERPRETER_ID, run_kernel_module)


__all__ = [
    "NODE_KERNEL_INTERPRETER_ID",
    "run_kernel_module",
]
