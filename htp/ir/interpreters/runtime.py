"""Object-owned runtime helpers for typed IR node execution."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..core.nodes import (
    BinaryExpr,
    BindingRef,
    ForStmt,
    Let,
    LiteralExpr,
    ReceiveExpr,
    Ref,
    Region,
    Return,
    SendStmt,
)


class ReturnSignal(Exception):
    """Structured early-return signal for kernel execution."""

    def __init__(self, value: Any) -> None:
        super().__init__("kernel_return")
        self.value = value


@dataclass
class ExecutionEnv:
    """Mutable execution environment shared by typed node interpreters."""

    env: dict[str, Any] = field(default_factory=dict)
    channels: dict[str, list[Any]] = field(default_factory=lambda: defaultdict(list))


class ExprEvaluator:
    """Evaluate typed expression nodes against an ``ExecutionEnv``."""

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
    """Execute typed statement nodes against an ``ExecutionEnv``."""

    expr_evaluator: ExprEvaluator

    def exec(self, statement: Any, env: ExecutionEnv) -> None:
        if isinstance(statement, Let):
            env.env[statement.symbol_id.value] = self.expr_evaluator.eval(statement.value, env)
            return
        if isinstance(statement, Return):
            raise ReturnSignal(self.expr_evaluator.eval(statement.value, env))
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


__all__ = ["ExecutionEnv", "ExprEvaluator", "ReturnSignal", "StmtExecutor"]
