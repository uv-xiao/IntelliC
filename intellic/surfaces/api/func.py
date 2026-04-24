from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable

from intellic.ir.dialects import func as func_dialect
from intellic.ir.syntax import Block, Region, Type, Value
from intellic.surfaces.api import builders


@dataclass(frozen=True)
class BuiltFunction:
    name: str
    operation: object
    evidence: tuple[str, ...]


def ir_function(fn: Callable[..., object]) -> BuiltFunction:
    signature = inspect.signature(fn)
    input_types = _input_types(signature)
    result_types = _result_types(signature)
    entry = Block(arg_types=input_types)
    body = Region.from_block_list([entry])
    with builders.construction_context(entry) as context:
        result = fn(*entry.arguments)
        return_values = _normalize_return(result)
        if len(return_values) != len(result_types):
            raise TypeError("function return count does not match annotation")
        for index, (value, expected_type) in enumerate(zip(return_values, result_types)):
            if value.type != expected_type:
                raise TypeError(f"function return {index} type does not match annotation")
        builders.emit(func_dialect.return_(*return_values), "builder:func.return")
        function_op = func_dialect.func(
            fn.__name__,
            func_dialect.FunctionType(inputs=input_types, results=result_types),
            body,
        )
        context.evidence.append(f"builder:func.func:{fn.__name__}")
        evidence = tuple(context.evidence)
    return BuiltFunction(fn.__name__, function_op, evidence)


def _input_types(signature: inspect.Signature) -> tuple[Type, ...]:
    types: list[Type] = []
    for parameter in signature.parameters.values():
        if parameter.annotation is inspect._empty:
            raise TypeError("function arguments require type annotation")
        if not isinstance(parameter.annotation, Type):
            raise TypeError("function argument annotation must be an IntelliC Type")
        types.append(parameter.annotation)
    return tuple(types)


def _result_types(signature: inspect.Signature) -> tuple[Type, ...]:
    annotation = signature.return_annotation
    if annotation is inspect._empty:
        raise TypeError("function return requires type annotation")
    if isinstance(annotation, Type):
        return (annotation,)
    if isinstance(annotation, tuple) and all(isinstance(item, Type) for item in annotation):
        return annotation
    raise TypeError("function return annotation must be an IntelliC Type")


def _normalize_return(result: object) -> tuple[Value, ...]:
    if isinstance(result, Value):
        return (result,)
    if isinstance(result, tuple) and all(isinstance(item, Value) for item in result):
        return result
    raise TypeError("function body must return IntelliC Value objects")
