from __future__ import annotations

from dataclasses import fields, is_dataclass
import json
from typing import Any

from .attribute import Attribute
from .operation import Operation
from .type import Type
from .value import Value


_OBJECT_PROPERTY_TYPES = frozenset(
    (
        "intellic.ir.syntax.attribute.Attribute",
        "intellic.ir.syntax.type.Type",
        "intellic.dialects.affine.AffineMap",
        "intellic.dialects.affine.AffineSet",
        "intellic.dialects.func.FunctionType",
        "intellic.dialects.memref.MemRefType",
        "intellic.dialects.vector.VectorType",
    )
)


class _Printer:
    def __init__(self) -> None:
        self._names: dict[Value, str] = {}
        self._next_value = 0
        self._next_block = 0

    def print_operation(self, op: Operation, indent: int = 0) -> str:
        prefix = " " * indent
        result_prefix = self._result_prefix(op)
        operands = ", ".join(self._value_name(operand) for operand in op.operands)
        properties = self._properties_suffix(op)
        operand_types = ", ".join(str(operand.type) for operand in op.operands)
        result_types = _format_function_results(tuple(result.type for result in op.results))
        if op.regions:
            lines = [
                f'{prefix}{result_prefix}"{op.name}"({operands}){properties} ({{',
            ]
            for region_index, region in enumerate(op.regions):
                if region_index > 0:
                    lines.append(f"{prefix}}}, {{")
                print_block_headers = len(region.blocks) > 1
                for block in region.blocks:
                    child_indent = indent + 2
                    if print_block_headers or block.arguments:
                        lines.append(self._print_block_header(block, indent + 2))
                        child_indent = indent + 4
                    for child in block.operations:
                        lines.append(self.print_operation(child, child_indent))
            lines.append(f"{prefix}}}) : ({operand_types}) -> {result_types}")
            return "\n".join(lines)
        return f'{prefix}{result_prefix}"{op.name}"({operands}){properties} : ({operand_types}) -> {result_types}'

    def _print_block_header(self, block, indent: int) -> str:
        name = f"^bb{self._next_block}"
        self._next_block += 1
        args = ", ".join(f"{self._assign_name(argument)}: {argument.type}" for argument in block.arguments)
        return f"{' ' * indent}{name}({args}):"

    def _result_prefix(self, op: Operation) -> str:
        if not op.results:
            return ""
        names = [self._assign_name(result) for result in op.results]
        return f"{', '.join(names)} = "

    def _properties_suffix(self, op: Operation) -> str:
        properties = {
            key: _encode_property(value)
            for key, value in sorted(op.properties.items())
        }
        if not properties:
            return ""
        return f" <{{{', '.join(f'{key} = {value}' for key, value in properties.items())}}}>"

    def _value_name(self, value: Value) -> str:
        if value not in self._names:
            self._assign_name(value)
        return self._names[value]

    def _assign_name(self, value: Value) -> str:
        name = f"%{self._next_value}"
        self._next_value += 1
        self._names[value] = name
        return name


def print_operation(op: Operation) -> str:
    """Print a deterministic generic MLIR-style operation form."""

    return _Printer().print_operation(op)


def _encode_property(value: Any) -> Any:
    if isinstance(value, str):
        return json.dumps(value)
    if value is None or isinstance(value, (bool, int, str)):
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return "none"
        return str(value)
    if isinstance(value, tuple):
        return f"[{', '.join(_encode_property(element) for element in value)}]"
    if isinstance(value, Type):
        return f"!intellic.type<{json.dumps(value.name)}>"
    if isinstance(value, Attribute):
        return f"#intellic.attr<{json.dumps(value.name)}, {_encode_property(value.value)}>"
    type_name = f"{type(value).__module__}.{type(value).__qualname__}"
    if type_name in _OBJECT_PROPERTY_TYPES and is_dataclass(value):
        encoded_fields = ", ".join(
            f"{field.name} = {_encode_property(getattr(value, field.name))}"
            for field in fields(value)
        )
        return f"#intellic.object<{json.dumps(type_name)}, {{{encoded_fields}}}>"
    raise TypeError(f"unsupported property value: {type_name}")


def _format_function_results(types: tuple[Type, ...]) -> str:
    if not types:
        return "()"
    if len(types) == 1:
        return str(types[0])
    return f"({', '.join(str(type_) for type_ in types)})"
