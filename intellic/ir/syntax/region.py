from __future__ import annotations

from collections.abc import Iterable

from .ids import SyntaxId
from .mutation_guard import GuardedList, record_direct_mutation_attempt
from .type import Type
from .value import BlockArgument


class Block:
    """Ordered operation list with typed block arguments."""

    def __setattr__(self, name: str, value: object) -> None:
        if name == "parent" and hasattr(self, "parent"):
            record_direct_mutation_attempt("block_parent_assignment", self)
        super().__setattr__(name, value)

    def __init__(self, arg_types: Iterable[Type] = ()) -> None:
        self.id = SyntaxId.fresh()
        self.parent: Region | None = None
        self.arguments = tuple(
            BlockArgument(self, index, type) for index, type in enumerate(arg_types)
        )
        super().__setattr__("_Block__operations", GuardedList(self, "_operations"))

    @property
    def _operations(self) -> GuardedList:
        return self.__operations

    @property
    def operations(self) -> tuple[object, ...]:
        return tuple(self._operations)

    def append_operation(self, op: object) -> None:
        self._operations.append(op)


class Region:
    """Ordered block list owned by an operation."""

    def __setattr__(self, name: str, value: object) -> None:
        if name == "parent" and hasattr(self, "parent"):
            record_direct_mutation_attempt("region_parent_assignment", self)
        super().__setattr__(name, value)

    def __init__(self, blocks: Iterable[Block] = ()) -> None:
        self.id = SyntaxId.fresh()
        self.parent: object | None = None
        super().__setattr__("_Region__blocks", GuardedList(self, "_blocks"))
        for block in blocks:
            self.append_block(block)

    @property
    def _blocks(self) -> GuardedList:
        return self.__blocks

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
