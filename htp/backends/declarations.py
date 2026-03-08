from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSolverDeclaration:
    backend: str
    variant: str
    hardware_profile: str
    target_capabilities: tuple[str, ...]
    supported_ops: tuple[str, ...]
    required_outputs: tuple[str, ...]


__all__ = ["BackendSolverDeclaration"]
