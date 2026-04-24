from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .attribute import Attribute
from .ids import SyntaxId
from .location import GENERATED, SourceLocation
from .type import Type
from .value import OpResult, Value


class Operation:
    """MLIR-style operation with operands, results, attributes, and regions."""

    def __init__(
        self,
        name: str,
        operands: tuple[Value, ...],
        result_types: tuple[Type, ...],
        properties: Mapping[str, Any],
        attributes: Mapping[str, Attribute],
        regions: tuple[object, ...],
        successors: tuple[object, ...],
        loc: SourceLocation,
    ) -> None:
        if "." not in name:
            raise ValueError("operation name must be fully qualified")
        self.id = SyntaxId.fresh()
        self.name = name
        self.parent: object | None = None
        self.operands = tuple(operands)
        self.properties = dict(properties)
        self.attributes = dict(attributes)
        self.regions = tuple(regions)
        self.successors = tuple(successors)
        self.loc = loc
        self.results = tuple(OpResult(self, index, type) for index, type in enumerate(result_types))

        for index, value in enumerate(self.operands):
            value.add_use(self, index)
        for region in self.regions:
            region.parent = self

    @classmethod
    def create(
        cls,
        name: str,
        operands: tuple[Value, ...] = (),
        result_types: tuple[Type, ...] = (),
        properties: Mapping[str, Any] | None = None,
        attributes: Mapping[str, Attribute] | None = None,
        regions: tuple[object, ...] = (),
        successors: tuple[object, ...] = (),
        loc: SourceLocation = GENERATED,
    ) -> "Operation":
        return cls(
            name=name,
            operands=operands,
            result_types=result_types,
            properties=properties or {},
            attributes=attributes or {},
            regions=regions,
            successors=successors,
            loc=loc,
        )

    def replace_operand(self, index: int, value: Value) -> None:
        old_value = self.operands[index]
        old_value.remove_use(self, index)
        operands = list(self.operands)
        operands[index] = value
        self.operands = tuple(operands)
        value.add_use(self, index)

    def erase_operand_uses(self) -> None:
        for index, value in enumerate(self.operands):
            value.remove_use(self, index)
