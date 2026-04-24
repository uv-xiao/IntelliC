from __future__ import annotations

from intellic.ir.dialects import arith as arith_dialect
from intellic.ir.syntax import Type, Value
from intellic.surfaces.api import builders


def constant(value: int, type: Type) -> Value:
    op = builders.emit(arith_dialect.constant(value, type), "builder:arith.constant")
    return op.results[0]


def addi(lhs: Value, rhs: Value) -> Value:
    op = builders.emit(arith_dialect.addi(lhs, rhs), "builder:arith.addi")
    return op.results[0]


def index_cast(value: Value, to_type: Type) -> Value:
    op = builders.emit(arith_dialect.index_cast(value, to_type), "builder:arith.index_cast")
    return op.results[0]
