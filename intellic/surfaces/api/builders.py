from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from intellic.ir.syntax import Block, Builder, Operation


@dataclass
class ConstructionContext:
    builder: Builder = field(default_factory=Builder)
    evidence: list[str] = field(default_factory=list)


_context_stack: list[ConstructionContext] = []


def current_context() -> ConstructionContext:
    if not _context_stack:
        raise ValueError("no active insertion point")
    return _context_stack[-1]


@contextmanager
def construction_context(block: Block) -> Iterator[ConstructionContext]:
    context = ConstructionContext()
    _context_stack.append(context)
    try:
        with context.builder.insert_at_end(block):
            yield context
    finally:
        _context_stack.pop()


def emit(op: Operation, evidence: str | None = None) -> Operation:
    context = current_context()
    inserted = context.builder.insert(op)
    context.evidence.append(evidence or f"builder:{op.name}")
    return inserted


@contextmanager
def nested_insertion(block: Block) -> Iterator[ConstructionContext]:
    context = current_context()
    with context.builder.insert_at_end(block):
        yield context
