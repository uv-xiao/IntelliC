"""Context and error helpers for AST-backed frontend capture."""

from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class FrontendSyntaxError(ValueError):
    """Structured frontend-syntax failure with source location."""

    def __init__(self, message: str, *, lineno: int | None = None, col_offset: int | None = None) -> None:
        location = []
        if lineno is not None:
            location.append(f"line {lineno}")
        if col_offset is not None:
            location.append(f"col {col_offset}")
        suffix = f" ({', '.join(location)})" if location else ""
        super().__init__(f"{message}{suffix}")


@dataclass(frozen=True)
class ASTFrontendFunction:
    """Resolved AST for one decorated program function."""

    function: Callable[..., Any]
    source: str
    module: ast.Module
    root: ast.FunctionDef


@dataclass
class ASTFrontendContext:
    """Mutable lowering context shared by small AST handler methods."""

    frontend_id: str
    dialect_id: str
    function_ast: ASTFrontendFunction
    kernel_spec: Any
    target: dict[str, Any]
    entry: str
    symbols: dict[str, Any] = field(default_factory=dict)
    locals: dict[str, Any] = field(default_factory=dict)
    emitted: dict[str, Any] = field(default_factory=dict)

    def fail(self, node: ast.AST, message: str) -> FrontendSyntaxError:
        return FrontendSyntaxError(
            message,
            lineno=getattr(node, "lineno", None),
            col_offset=getattr(node, "col_offset", None),
        )


def load_function_ast(function: Callable[..., Any]) -> ASTFrontendFunction:
    """Resolve one Python function into a dedented AST."""

    source = textwrap.dedent(inspect.getsource(function))
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function.__name__:
            return ASTFrontendFunction(function=function, source=source, module=module, root=node)
    raise FrontendSyntaxError(f"Could not locate function AST for {function.__name__}")


__all__ = ["ASTFrontendContext", "ASTFrontendFunction", "FrontendSyntaxError", "load_function_ast"]
