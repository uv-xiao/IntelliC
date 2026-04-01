"""Shared AST-lowering helpers for small dialect frontend handlers."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from typing import Any

from .ast_context import ASTFrontendContext
from .ast_visitor import ASTFrontendVisitor


def sequence_values(node: ast.AST | None) -> tuple[ast.AST, ...]:
    if node is None:
        return ()
    if isinstance(node, (ast.List, ast.Tuple)):
        return tuple(node.elts)
    return (node,)


def literal_or_default(node: ast.AST | None, *, default: Any) -> Any:
    if node is None:
        return default
    return ast.literal_eval(node)


def literal_or_none(node: ast.AST | None) -> Any:
    if node is None:
        return None
    return ast.literal_eval(node)


def default_kernel_args(kernel_spec: Any) -> tuple[str, ...]:
    return tuple(argument.name for argument in kernel_spec.args if argument.name is not None)


def resolve_surface_value(
    node: ast.AST | None,
    context: ASTFrontendContext,
    *,
    prefer_symbols: bool = True,
    prefer_locals: bool = True,
) -> Any:
    if node is None:
        return None
    path = ASTFrontendVisitor.attribute_path(node)
    if len(path) == 3 and path[1] == "args":
        return path[2]
    if isinstance(node, ast.Name):
        if prefer_symbols and node.id in context.symbols:
            return context.symbols[node.id]
        if prefer_locals and node.id in context.locals:
            return context.locals[node.id]
        return node.id
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [resolve_surface_value(item, context) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            resolve_surface_value(key, context): resolve_surface_value(value, context)
            for key, value in zip(node.keys, node.values, strict=False)
        }
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError) as exc:
        raise context.fail(node, "Unsupported frontend expression") from exc


def resolved_keyword_map(call: ast.Call, context: ASTFrontendContext) -> dict[str, Any]:
    return {
        item.arg: resolve_surface_value(item.value, context) for item in call.keywords if item.arg is not None
    }


def keyword_or_default(
    call: ast.Call,
    key: str,
    default: Any,
    context: ASTFrontendContext,
) -> Any:
    for item in call.keywords:
        if item.arg == key:
            return resolve_surface_value(item.value, context)
    return default


def resolve_name(node: ast.AST, context: ASTFrontendContext, *, failure: str) -> str:
    value = resolve_surface_value(node, context)
    if isinstance(value, str):
        return value
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    raise context.fail(node, failure)


def surface_ref(*, node_id: str, name: str):
    from htp.ir.core.nodes import ref

    return ref(node_id, f"sym.{name}", name)


def ordered_resolved_values(
    nodes: Iterable[ast.AST],
    context: ASTFrontendContext,
) -> tuple[Any, ...]:
    return tuple(resolve_surface_value(node, context) for node in nodes)


__all__ = [
    "default_kernel_args",
    "keyword_or_default",
    "literal_or_default",
    "literal_or_none",
    "ordered_resolved_values",
    "resolve_name",
    "resolve_surface_value",
    "resolved_keyword_map",
    "sequence_values",
    "surface_ref",
]
