from __future__ import annotations

from .operation import Operation


def print_operation(op: Operation) -> str:
    """Return a minimal generic spelling for early syntax tests."""

    return f'"{op.name}"()'
