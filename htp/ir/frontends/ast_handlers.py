"""Shared handler metadata for AST-backed frontend capture."""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ASTHandlerSpec:
    """One AST handler registration on a visitor method."""

    node_type: type[ast.AST]
    decorator: str | None = None
    call: str | None = None


def handles(
    node_type: type[ast.AST],
    *,
    decorator: str | None = None,
    call: str | None = None,
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Attach AST dispatch metadata to a visitor method."""

    def decorator_fn(method: Callable[..., object]) -> Callable[..., object]:
        specs = list(getattr(method, "__htp_ast_handler_specs__", ()))
        specs.append(ASTHandlerSpec(node_type=node_type, decorator=decorator, call=call))
        setattr(method, "__htp_ast_handler_specs__", tuple(specs))
        return method

    return decorator_fn


__all__ = ["ASTHandlerSpec", "handles"]
