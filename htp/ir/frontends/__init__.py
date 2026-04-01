"""Frontend registry and lowering substrate."""

from .builtin import ensure_builtin_frontends
from .registry import FrontendSpec, frontend_registry_snapshot, register_frontend, resolve_frontend
from .rules import FrontendBuildContext, FrontendRule, FrontendRuleResult, ProgramSurfaceRule
from .shared import FrontendWorkload, build_frontend_program_module, kernel_spec_from_payload

__all__ = [
    "FrontendBuildContext",
    "FrontendRule",
    "FrontendRuleResult",
    "FrontendSpec",
    "FrontendWorkload",
    "ProgramSurfaceRule",
    "build_frontend_program_module",
    "ensure_builtin_frontends",
    "frontend_registry_snapshot",
    "kernel_spec_from_payload",
    "register_frontend",
    "resolve_frontend",
]
