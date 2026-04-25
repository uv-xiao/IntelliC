from __future__ import annotations

import ast
import re
from collections.abc import Callable
from importlib import import_module

from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, Type, Value
from intellic.ir.parser.lexer import strip_comments


_PROPERTIES_RE = r"(?:\s+<\{(?P<properties>.*)\}>)?"
_OP_RE = re.compile(
    r'^(?:(?P<results>%[\w.]+(?:\s*,\s*%[\w.]+)*)\s*=\s*)?'
    r'"(?P<name>[^"]+)"\((?P<operands>[^)]*)\)'
    + _PROPERTIES_RE +
    r'(?P<region>\s*\(\{)?\s*:\s*\((?P<operand_types>[^)]*)\)\s*->\s*(?P<result_types>.+)$'
)
_REGION_START_RE = re.compile(
    r'^(?:(?P<results>%[\w.]+(?:\s*,\s*%[\w.]+)*)\s*=\s*)?'
    r'"(?P<name>[^"]+)"\((?P<operands>[^)]*)\)'
    + _PROPERTIES_RE +
    r"\s*\(\{$"
)
_REGION_SEPARATOR_RE = re.compile(r"^\},\s*\{$")
_REGION_END_RE = re.compile(r"^\}\)\s*:\s*\((?P<operand_types>[^)]*)\)\s*->\s*(?P<result_types>.+)$")
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
        self._value_scopes: list[dict[str, Value]] = [{}]

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
        result_types = self._parse_result_types(op_match.group("result_types"))
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
        operands = self._parse_operands(match.group("operands"))
        properties = self._parse_properties(match.group("properties"))
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
        result_types = self._parse_result_types(end_match.group("result_types"))
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
        self._push_scope()
        try:
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
        finally:
            self._pop_scope()

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
            if name in self._value_scopes[-1]:
                raise ValueError(f"duplicate SSA value: {name}")
            self._value_scopes[-1][name] = argument
        return block

    def _parse_operands(self, text: str) -> tuple[Value, ...]:
        names = [part.strip() for part in text.split(",") if part.strip()]
        operands: list[Value] = []
        for name in names:
            operands.append(self._lookup_value(name))
        return tuple(operands)

    def _parse_types(self, text: str) -> tuple[Type, ...]:
        return tuple(Type(part.strip()) for part in text.split(",") if part.strip())

    def _parse_result_types(self, text: str) -> tuple[Type, ...]:
        text = text.strip()
        if text == "()":
            return ()
        if text.startswith("(") and text.endswith(")"):
            return self._parse_types(text[1:-1])
        return (Type(text),)

    def _parse_properties(self, text: str | None) -> dict[str, object]:
        if not text:
            return {}
        return _parse_property_dict_body(text)

    def _lookup_value(self, name: str) -> Value:
        for scope in reversed(self._value_scopes):
            if name in scope:
                return scope[name]
        raise ValueError(f"unknown SSA value: {name}")

    def _push_scope(self) -> None:
        self._value_scopes.append({})

    def _pop_scope(self) -> None:
        self._value_scopes.pop()

    def _bind_results(self, names_text: str | None, op: Operation) -> None:
        if not names_text:
            if op.results:
                raise ValueError("operation results require SSA names")
            return
        names = [part.strip() for part in names_text.split(",")]
        if len(names) != len(op.results):
            raise ValueError("SSA result count does not match operation result types")
        for name, value in zip(names, op.results):
            if name in self._value_scopes[-1]:
                raise ValueError(f"duplicate SSA value: {name}")
            self._value_scopes[-1][name] = value


_PROPERTY_CODECS: dict[str, Callable[..., object]] = {}


def _parse_property_dict_body(text: str) -> dict[str, object]:
    text = text.strip()
    if not text:
        return {}
    properties: dict[str, object] = {}
    for entry in _split_top_level(text):
        if "=" not in entry:
            raise ValueError("expected property assignment")
        key, value_text = [part.strip() for part in entry.split("=", 1)]
        if not key:
            raise ValueError("expected property name")
        properties[key] = _parse_property_value(value_text)
    return properties


def _parse_property_value(text: str) -> object:
    text = text.strip()
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "none":
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if text.startswith('"') and text.endswith('"'):
        return ast.literal_eval(text)
    if text.startswith("[") and text.endswith("]"):
        body = text[1:-1].strip()
        if not body:
            return ()
        return tuple(_parse_property_value(element) for element in _split_top_level(body))
    if text.startswith("!intellic.type<") and text.endswith(">"):
        return Type(ast.literal_eval(text.removeprefix("!intellic.type<")[:-1]))
    if text.startswith("#intellic.attr<") and text.endswith(">"):
        payload = text.removeprefix("#intellic.attr<")[:-1]
        parts = _split_top_level(payload)
        if len(parts) != 2:
            raise ValueError("malformed attribute property")
        return Attribute(ast.literal_eval(parts[0].strip()), _parse_property_value(parts[1]))
    if text.startswith("#intellic.object<") and text.endswith(">"):
        payload = text.removeprefix("#intellic.object<")[:-1]
        parts = _split_top_level(payload)
        if len(parts) != 2:
            raise ValueError("malformed object property")
        type_name = ast.literal_eval(parts[0].strip())
        fields_text = parts[1].strip()
        if not fields_text.startswith("{") or not fields_text.endswith("}"):
            raise ValueError("malformed object property fields")
        return _property_constructor(type_name)(**_parse_property_dict_body(fields_text[1:-1]))
    raise ValueError(f"unsupported property value: {text}")


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    angle_depth = 0
    square_depth = 0
    brace_depth = 0
    paren_depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "<":
            angle_depth += 1
        elif char == ">":
            angle_depth -= 1
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "," and not any((angle_depth, square_depth, brace_depth, paren_depth)):
            parts.append(text[start:index].strip())
            start = index + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _property_constructor(type_name: str) -> Callable[..., object]:
    _ensure_property_codecs()
    try:
        return _PROPERTY_CODECS[type_name]
    except KeyError as exc:
        raise ValueError(f"unknown property codec: {type_name}") from exc


def _ensure_property_codecs() -> None:
    if _PROPERTY_CODECS:
        return
    for module_name, class_name in (
        ("intellic.ir.syntax.attribute", "Attribute"),
        ("intellic.ir.syntax.type", "Type"),
        ("intellic.dialects.affine", "AffineMap"),
        ("intellic.dialects.affine", "AffineSet"),
        ("intellic.dialects.func", "FunctionType"),
        ("intellic.dialects.memref", "MemRefType"),
        ("intellic.dialects.vector", "VectorType"),
    ):
        cls = getattr(import_module(module_name), class_name)
        _PROPERTY_CODECS[f"{module_name}.{class_name}"] = cls
