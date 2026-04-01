"""Dialect registry and dialect-specific typed structures."""

from .registry import (
    DialectActivation,
    DialectExports,
    DialectSpec,
    activate_dialects,
    dialect_activation_payload,
    dialect_registry_snapshot,
    ensure_builtin_dialects,
    get_dialect,
    register_dialect,
    resolve_dialects,
)

__all__ = [
    "DialectActivation",
    "DialectExports",
    "DialectSpec",
    "activate_dialects",
    "dialect_activation_payload",
    "dialect_registry_snapshot",
    "ensure_builtin_dialects",
    "get_dialect",
    "register_dialect",
    "resolve_dialects",
]
