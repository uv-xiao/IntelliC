from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from .operation import Operation
from .region import Block


@dataclass(frozen=True)
class InsertionPoint:
    block: Block


class Builder:
    """Controlled operation insertion API."""

    def __init__(self) -> None:
        self._stack: list[InsertionPoint] = []

    @contextmanager
    def insert_at_end(self, block: Block) -> Iterator["Builder"]:
        self._stack.append(InsertionPoint(block))
        try:
            yield self
        finally:
            self._stack.pop()

    @property
    def insertion_point(self) -> InsertionPoint:
        if not self._stack:
            raise ValueError("no active insertion point")
        return self._stack[-1]

    def insert(self, op: Operation) -> Operation:
        if op.parent is not None:
            raise ValueError("operation already has a parent")
        block = self.insertion_point.block
        op.parent = block
        block.append_operation(op)
        return op
