from __future__ import annotations

from dataclasses import dataclass

from intellic.ir.syntax import Operation, Region, Type, Value


@dataclass(frozen=True)
class FunctionType:
    inputs: tuple[Type, ...] = ()
    results: tuple[Type, ...] = ()


def func(name: str, function_type: FunctionType, body: Region) -> Operation:
    return Operation.create(
        "func.func",
        result_types=(),
        properties={"sym_name": name, "function_type": function_type},
        regions=(body,),
    )


def call(callee: str, operands: tuple[Value, ...], function_type: FunctionType) -> Operation:
    if len(operands) != len(function_type.inputs):
        raise ValueError("func.call operand count does not match callee type")
    for index, (operand, expected_type) in enumerate(zip(operands, function_type.inputs)):
        if operand.type != expected_type:
            raise TypeError(f"func.call operand {index} type mismatch")
    return Operation.create(
        "func.call",
        operands=operands,
        result_types=function_type.results,
        properties={"callee": callee, "function_type": function_type},
    )


def return_(*operands: Value) -> Operation:
    return Operation.create("func.return", operands=tuple(operands))
