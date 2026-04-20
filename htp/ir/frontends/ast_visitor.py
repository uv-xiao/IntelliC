"""Object-oriented AST frontend visitor substrate."""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .ast_context import ASTFrontendContext, ASTFrontendFunction, FrontendSyntaxError
from .ast_handlers import ASTHandlerSpec


@dataclass(frozen=True)
class _BoundHandler:
    spec: ASTHandlerSpec
    method: Callable[..., object]


class ASTFrontendVisitor:
    """Shared AST-dispatch engine for dialect-specific frontend capture."""

    def __init__(self) -> None:
        self._handlers = self._collect_handlers()

    def dispatch(self, node: ast.AST, context: ASTFrontendContext) -> object:
        decorator_name = self.decorator_name(node)
        call_name = self.call_name(node)
        for handler in self._handlers:
            if not isinstance(node, handler.spec.node_type):
                continue
            if handler.spec.decorator is not None and handler.spec.decorator != decorator_name:
                continue
            if handler.spec.call is not None and handler.spec.call != call_name:
                continue
            return handler.method(node, context)
        raise context.fail(node, f"No AST frontend handler for {type(node).__name__}")

    def build_context(
        self,
        *,
        frontend_id: str,
        dialect_id: str,
        function_ast: ASTFrontendFunction,
        kernel_spec: Any,
        target: dict[str, Any],
        entry: str,
    ) -> ASTFrontendContext:
        return ASTFrontendContext(
            frontend_id=frontend_id,
            dialect_id=dialect_id,
            function_ast=function_ast,
            kernel_spec=kernel_spec,
            target=target,
            entry=entry,
        )

    @staticmethod
    def decorator_name(node: ast.AST) -> str | None:
        if not isinstance(node, ast.FunctionDef):
            return None
        if not node.decorator_list:
            return None
        decorator = node.decorator_list[0]
        if isinstance(decorator, ast.Call):
            return ASTFrontendVisitor.call_name(decorator)
        if isinstance(decorator, ast.Attribute):
            return decorator.attr
        if isinstance(decorator, ast.Name):
            return decorator.id
        return None

    @staticmethod
    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Expr):
            return ASTFrontendVisitor.call_name(node.value)
        if isinstance(node, ast.Assign):
            return ASTFrontendVisitor.call_name(node.value)
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Attribute):
                return function.attr
            if isinstance(function, ast.Name):
                return function.id
        return None

    @staticmethod
    def attribute_path(node: ast.AST) -> tuple[str, ...]:
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return tuple(reversed(parts))
        return ()

    @staticmethod
    def literal_value(node: ast.AST) -> Any:
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError) as exc:
            raise FrontendSyntaxError("Expression is not a supported literal") from exc

    def _collect_handlers(self) -> tuple[_BoundHandler, ...]:
        handlers: list[_BoundHandler] = []
        for name in dir(self):
            method = getattr(self, name)
            specs = getattr(method, "__htp_ast_handler_specs__", ())
            for spec in specs:
                handlers.append(_BoundHandler(spec=spec, method=method))
        handlers.sort(
            key=lambda handler: (
                handler.spec.decorator is not None,
                handler.spec.call is not None,
            ),
            reverse=True,
        )
        return tuple(handlers)


__all__ = ["ASTFrontendVisitor", "FrontendSyntaxError"]
