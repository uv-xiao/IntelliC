from __future__ import annotations

from intellic.ir.syntax import Operation, Region


def module(region: Region) -> Operation:
    return Operation.create("builtin.module", regions=(region,))
