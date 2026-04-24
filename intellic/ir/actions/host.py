from __future__ import annotations

from .action import CompilerAction


def fixed_action(name, apply):
    return CompilerAction(name, apply)
