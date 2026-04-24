from __future__ import annotations

from typing import Any

from .attribute import Attribute
from .operation import Operation
from .value import Value


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
        result_types = ", ".join(str(result.type) for result in op.results)
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
            lines.append(f"{prefix}}}) : () -> ({result_types})")
            return "\n".join(lines)
        return f'{prefix}{result_prefix}"{op.name}"({operands}){properties} : () -> ({result_types})'

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
            if _is_printable_property(value)
        }
        if not properties:
            return ""
        return f" {properties!r}"

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


def _is_printable_property(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, Attribute):
        return _is_printable_property(value.value)
    if isinstance(value, tuple):
        return all(_is_printable_property(element) for element in value)
    return False


def _encode_property(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Attribute):
        return {
            "__intellic_attribute__": (
                value.name,
                _encode_property(value.value),
            )
        }
    if isinstance(value, tuple):
        return tuple(_encode_property(element) for element in value)
    raise TypeError(f"unsupported printable property: {type(value).__name__}")
