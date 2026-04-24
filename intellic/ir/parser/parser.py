from __future__ import annotations

import re

from intellic.ir.syntax import Block, Builder, Operation, Region, Type, Value
from intellic.ir.parser.lexer import strip_comments


_OP_RE = re.compile(
    r'^(?:(?P<results>%[\w.]+(?:\s*,\s*%[\w.]+)*)\s*=\s*)?'
    r'"(?P<name>[^"]+)"\((?P<operands>[^)]*)\)'
    r'(?P<region>\s*\(\{)?\s*:\s*\(\)\s*->\s*\((?P<result_types>[^)]*)\)$'
)
_REGION_START_RE = re.compile(
    r'^(?:(?P<results>%[\w.]+(?:\s*,\s*%[\w.]+)*)\s*=\s*)?'
    r'"(?P<name>[^"]+)"\((?P<operands>[^)]*)\)\s*\(\{$'
)
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
        result_types = self._parse_types(op_match.group("result_types"))
        op = Operation.create(op_match.group("name"), operands=operands, result_types=result_types)
        self._bind_results(op_match.group("results"), op)
        return op

    def _parse_region_operation(self, match: re.Match[str]) -> Operation:
        self.index += 1
        block = self._parse_optional_block()
        region = Region.from_block_list([block])
        children: list[Operation] = []
        while self.has_more and not _REGION_END_RE.match(self.lines[self.index]):
            children.append(self.parse_one())
        if not self.has_more:
            raise ValueError("unterminated region")
        end_match = _REGION_END_RE.match(self.lines[self.index])
        assert end_match is not None
        self.index += 1
        with Builder().insert_at_end(block) as builder:
            for child in children:
                builder.insert(child)
        operands = self._parse_operands(match.group("operands"))
        result_types = self._parse_types(end_match.group("result_types"))
        op = Operation.create(match.group("name"), operands=operands, result_types=result_types, regions=(region,))
        self._bind_results(match.group("results"), op)
        return op

    def _parse_optional_block(self) -> Block:
        if not self.has_more:
            return Block()
        block_match = _BLOCK_RE.match(self.lines[self.index])
        if block_match is None:
            return Block()
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
