from __future__ import annotations

from collections.abc import Iterable

from .ids import SyntaxId
from .mutation_guard import GuardedList
from .type import Type
from .value import BlockArgument


class Block:
    """Ordered operation list with typed block arguments."""

    def __init__(self, arg_types: Iterable[Type] = ()) -> None:
        self.id = SyntaxId.fresh()
        self.parent: Region | None = None
        self.arguments = tuple(
            BlockArgument(self, index, type) for index, type in enumerate(arg_types)
        )
        self._operations: list[object] = GuardedList(self, "_operations")

    @property
    def operations(self) -> tuple[object, ...]:
        return tuple(self._operations)

    def append_operation(self, op: object) -> None:
        self._operations.append(op)


class Region:
    """Ordered block list owned by an operation."""

    def __init__(self, blocks: Iterable[Block] = ()) -> None:
        self.id = SyntaxId.fresh()
        self.parent: object | None = None
        self._blocks: list[Block] = GuardedList(self, "_blocks")
        for block in blocks:
            self.append_block(block)

    @classmethod
    def from_block_list(cls, blocks: Iterable[Block]) -> "Region":
        return cls(blocks)

    @property
    def blocks(self) -> tuple[Block, ...]:
        return tuple(self._blocks)

    def append_block(self, block: Block) -> None:
        if block.parent is not None:
            raise ValueError("block already has a parent")
        block.parent = self
        self._blocks.append(block)
