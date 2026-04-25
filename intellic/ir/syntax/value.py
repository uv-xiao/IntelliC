from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .ids import SyntaxId
from .type import Type

if TYPE_CHECKING:
    from .operation import Operation
    from .region import Block


@dataclass(frozen=True)
class Use:
    """One operand use of an SSA value."""

    value: "Value"
    owner: "Operation"
    operand_index: int


class Value:
    """Base class for SSA values."""

    def __init__(self, type: Type) -> None:
        self.id = SyntaxId.fresh()
        self.type = type
        self._uses: tuple[Use, ...] = ()

    @property
    def uses(self) -> tuple[Use, ...]:
        return self._uses

    def add_use(self, owner: "Operation", operand_index: int) -> Use:
        use = Use(self, owner, operand_index)
        self._uses = self._uses + (use,)
        return use

    def remove_use(self, owner: "Operation", operand_index: int) -> None:
        self._uses = tuple(
            use
            for use in self._uses
            if not (use.owner is owner and use.operand_index == operand_index)
        )

    def __bool__(self) -> bool:
        raise TypeError("symbolic IR value cannot be used as a Python bool")


class OpResult(Value):
    """SSA value produced by an operation result."""

    def __init__(self, owner: "Operation", index: int, type: Type) -> None:
        super().__init__(type)
        self.owner = owner
        self.index = index


class BlockArgument(Value):
    """SSA value owned by a block argument."""

    def __init__(self, owner: "Block", index: int, type: Type) -> None:
        super().__init__(type)
        self.owner = owner
        self.index = index
