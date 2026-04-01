"""Frontend registry and lowering substrate."""

from .ast_context import ASTFrontendContext, ASTFrontendFunction, FrontendSyntaxError, load_function_ast
from .ast_handlers import ASTHandlerSpec, handles
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
    "ensure_builtin_frontends",
    "frontend_registry_snapshot",
    "handles",
    "kernel_spec_from_payload",
    "load_function_ast",
    "register_frontend",
    "resolve_frontend",
]
