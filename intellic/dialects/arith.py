from __future__ import annotations

from intellic.ir.syntax import Operation, Type, Value, i32, index


def constant(value: int, type: Type) -> Operation:
    return Operation.create(
        "arith.constant",
        result_types=(type,),
        properties={"value": value},
    )


def addi(lhs: Value, rhs: Value) -> Operation:
    if lhs.type != rhs.type:
        raise TypeError("arith.addi operands must have the same type")
    return Operation.create("arith.addi", operands=(lhs, rhs), result_types=(lhs.type,))


def index_cast(value: Value, to_type: Type) -> Operation:
    if value.type not in (index, i32) or to_type not in (index, i32):
        raise TypeError("arith.index_cast supports index/i32 in the first slice")
    return Operation.create(
        "arith.index_cast",
        operands=(value,),
        result_types=(to_type,),
        properties={"to_type": to_type},
    )
