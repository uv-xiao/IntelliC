"""Lazy verifier bootstrap for first-slice dialect modules."""

from __future__ import annotations

from importlib import import_module

from intellic.ir.syntax.verify import register_operation_verifier_loader


def _load_module(module_name: str) -> None:
    import_module(module_name)


register_operation_verifier_loader(
    "scf.",
    lambda: _load_module("intellic.ir.dialects.scf"),
)
