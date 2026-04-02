"""Frontend registry and lowering substrate."""

from .ast_context import ASTFrontendContext, ASTFrontendFunction, FrontendSyntaxError, load_function_ast
from .ast_handlers import ASTHandlerSpec, handles
from .ast_lowering import (
    default_kernel_args,
    keyword_or_default,
    literal_or_default,
    literal_or_none,
    ordered_resolved_values,
    resolve_name,
    resolve_surface_value,
    resolved_keyword_map,
    sequence_values,
    surface_ref,
)
from .ast_visitor import ASTFrontendVisitor
from .builtin import ensure_builtin_frontends
from .registry import FrontendSpec, frontend_registry_snapshot, register_frontend, resolve_frontend
from .rules import FrontendBuildContext, FrontendRule, FrontendRuleResult, ProgramSurfaceRule
from .shared import FrontendWorkload, build_frontend_program_module, kernel_spec_from_payload

__all__ = [
    "ASTFrontendContext",
    "ASTFrontendFunction",
    "ASTFrontendVisitor",
    "ASTHandlerSpec",
    "FrontendBuildContext",
    "FrontendRule",
    "FrontendRuleResult",
    "FrontendSyntaxError",
    "FrontendSpec",
    "FrontendWorkload",
    "ProgramSurfaceRule",
    "build_frontend_program_module",
    "default_kernel_args",
    "ensure_builtin_frontends",
    "frontend_registry_snapshot",
    "handles",
    "keyword_or_default",
    "kernel_spec_from_payload",
    "literal_or_default",
    "literal_or_none",
    "load_function_ast",
    "ordered_resolved_values",
    "register_frontend",
    "resolve_name",
    "resolve_frontend",
    "resolve_surface_value",
    "resolved_keyword_map",
    "sequence_values",
    "surface_ref",
]
