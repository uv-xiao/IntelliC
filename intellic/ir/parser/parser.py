from __future__ import annotations

import ast
import re

from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, Type, Value
from intellic.ir.parser.lexer import strip_comments


_PROPERTIES_RE = r"(?:\s+(?P<properties>\{.*\}))?"
_OP_RE = re.compile(
    r'^(?:(?P<results>%[\w.]+(?:\s*,\s*%[\w.]+)*)\s*=\s*)?'
    r'"(?P<name>[^"]+)"\((?P<operands>[^)]*)\)'
    + _PROPERTIES_RE +
    r'(?P<region>\s*\(\{)?\s*:\s*\(\)\s*->\s*\((?P<result_types>[^)]*)\)$'
)
_REGION_START_RE = re.compile(
    r'^(?:(?P<results>%[\w.]+(?:\s*,\s*%[\w.]+)*)\s*=\s*)?'
    r'"(?P<name>[^"]+)"\((?P<operands>[^)]*)\)'
    + _PROPERTIES_RE +
    r"\s*\(\{$"
)
_REGION_SEPARATOR_RE = re.compile(r"^\},\s*\{$")
_REGION_END_RE = re.compile(r"^\}\)\s*:\s*\(\)\s*->\s*\((?P<result_types>[^)]*)\)$")
_BLOCK_RE = re.compile(r"^\^(?P<label>[\w.]+)\((?P<args>.*)\):$")


def parse_operation(text: str) -> Operation:
    lines = [line.strip() for line in strip_comments(text).splitlines() if line.strip()]
    if not lines:
        raise ValueError("expected operation")
    parser = _Parser(lines)
    op = parser.parse_one()
    if parser.has_more:
        raise ValueError("unexpected trailing input")
    return op


class _Parser:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.index = 0
        self.values: dict[str, Value] = {}

    @property
    def has_more(self) -> bool:
        return self.index < len(self.lines)

    def parse_one(self) -> Operation:
        if not self.has_more:
            raise ValueError("expected operation")
        line = self.lines[self.index]
        region_match = _REGION_START_RE.match(line)
        if region_match:
            return self._parse_region_operation(region_match)
        op_match = _OP_RE.match(line)
        if not op_match:
            raise ValueError("expected operation")
        self.index += 1
        operands = self._parse_operands(op_match.group("operands"))
        properties = self._parse_properties(op_match.group("properties"))
        result_types = self._parse_types(op_match.group("result_types"))
        op = Operation.create(
            op_match.group("name"),
            operands=operands,
            result_types=result_types,
            properties=properties,
        )
        self._bind_results(op_match.group("results"), op)
        return op

    def _parse_region_operation(self, match: re.Match[str]) -> Operation:
        self.index += 1
        regions: list[Region] = []
        end_match: re.Match[str] | None = None
        while True:
            region = self._parse_region_body()
            if not self.has_more:
                raise ValueError("unterminated region")
            regions.append(region)
            if _REGION_SEPARATOR_RE.match(self.lines[self.index]):
                self.index += 1
                continue
            end_match = _REGION_END_RE.match(self.lines[self.index])
            assert end_match is not None
            self.index += 1
            break
        operands = self._parse_operands(match.group("operands"))
        properties = self._parse_properties(match.group("properties"))
        result_types = self._parse_types(end_match.group("result_types"))
        op = Operation.create(
            match.group("name"),
            operands=operands,
            result_types=result_types,
            properties=properties,
            regions=tuple(regions),
        )
        self._bind_results(match.group("results"), op)
        return op

    def _parse_region_body(self) -> Region:
        blocks: list[Block] = []
        if self._at_region_boundary():
            return Region.from_block_list([Block()])
        while self.has_more and not self._at_region_boundary():
            if _BLOCK_RE.match(self.lines[self.index]):
                block = self._parse_block_header()
                self._parse_block_operations(block)
                blocks.append(block)
                continue
            if blocks:
                raise ValueError("expected block header")
            block = Block()
            self._parse_block_operations(block)
            blocks.append(block)
        return Region.from_block_list(blocks)

    def _parse_block_operations(self, block: Block) -> None:
        children: list[Operation] = []
        while (
            self.has_more
            and not self._at_region_boundary()
            and not _BLOCK_RE.match(self.lines[self.index])
        ):
            children.append(self.parse_one())
        with Builder().insert_at_end(block) as builder:
            for child in children:
                builder.insert(child)

    def _at_region_boundary(self) -> bool:
        return (
            self.has_more
            and (
                _REGION_SEPARATOR_RE.match(self.lines[self.index]) is not None
                or _REGION_END_RE.match(self.lines[self.index]) is not None
            )
        )

    def _parse_block_header(self) -> Block:
        block_match = _BLOCK_RE.match(self.lines[self.index])
        assert block_match is not None
        self.index += 1
        arg_specs = [part.strip() for part in block_match.group("args").split(",") if part.strip()]
        names: list[str] = []
        types: list[Type] = []
        for spec in arg_specs:
            if ":" not in spec:
                raise ValueError("expected block argument type")
            name, type_text = [part.strip() for part in spec.split(":", 1)]
            names.append(name)
            types.append(Type(type_text))
        block = Block(arg_types=types)
        for name, argument in zip(names, block.arguments):
            if name in self.values:
                raise ValueError(f"duplicate SSA value: {name}")
            self.values[name] = argument
        return block

    def _parse_operands(self, text: str) -> tuple[Value, ...]:
        names = [part.strip() for part in text.split(",") if part.strip()]
        operands: list[Value] = []
        for name in names:
            try:
                operands.append(self.values[name])
            except KeyError as exc:
                raise ValueError(f"unknown SSA value: {name}") from exc
        return tuple(operands)

    def _parse_types(self, text: str) -> tuple[Type, ...]:
        return tuple(Type(part.strip()) for part in text.split(",") if part.strip())

    def _parse_properties(self, text: str | None) -> dict[str, object]:
        if not text:
            return {}
        value = ast.literal_eval(text)
        if not isinstance(value, dict):
            raise ValueError("operation properties must be a dictionary")
        return {
            key: self._decode_property(property_value)
            for key, property_value in value.items()
        }

    def _decode_property(self, value: object) -> object:
        if (
            isinstance(value, dict)
            and set(value) == {"__intellic_attribute__"}
        ):
            payload = value["__intellic_attribute__"]
            if (
                not isinstance(payload, tuple)
                or len(payload) != 2
                or not isinstance(payload[0], str)
            ):
                raise ValueError("malformed attribute property")
            return Attribute(payload[0], self._decode_property(payload[1]))
        if isinstance(value, tuple):
            return tuple(self._decode_property(element) for element in value)
        return value

    def _bind_results(self, names_text: str | None, op: Operation) -> None:
        if not names_text:
            if op.results:
                raise ValueError("operation results require SSA names")
            return
        names = [part.strip() for part in names_text.split(",")]
        if len(names) != len(op.results):
            raise ValueError("SSA result count does not match operation result types")
        for name, value in zip(names, op.results):
            if name in self.values:
                raise ValueError(f"duplicate SSA value: {name}")
            self.values[name] = value
