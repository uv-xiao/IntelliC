from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .attribute import Attribute
from .ids import SyntaxId
from .location import GENERATED, SourceLocation
from .mutation_guard import GuardedDict, record_direct_mutation_attempt
from .type import Type
from .value import OpResult, Value


class Operation:
    """MLIR-style operation with operands, results, attributes, and regions."""

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "operands":
            if hasattr(self, "operands"):
                record_direct_mutation_attempt("operand_assignment", self)
            self._set_operands_unchecked(value)
            return
        if name == "properties":
            if hasattr(self, "properties"):
                record_direct_mutation_attempt("metadata_assignment", self, field=name)
            if not isinstance(value, GuardedDict):
                value = GuardedDict(self, name, value)
            self._set_properties_unchecked(value)
            return
        if name == "attributes":
            if hasattr(self, "attributes"):
                record_direct_mutation_attempt("metadata_assignment", self, field=name)
            if not isinstance(value, GuardedDict):
                value = GuardedDict(self, name, value)
            self._set_attributes_unchecked(value)
            return
        super().__setattr__(name, value)

    @property
    def operands(self) -> tuple[Value, ...]:
        return self.__operands

    @property
    def properties(self) -> GuardedDict:
        return self.__properties

    @property
    def attributes(self) -> GuardedDict:
        return self.__attributes

    def _set_operands_unchecked(self, operands: tuple[Value, ...]) -> None:
        super().__setattr__("_Operation__operands", tuple(operands))

    def _set_properties_unchecked(self, properties: GuardedDict) -> None:
        super().__setattr__("_Operation__properties", properties)

    def _set_attributes_unchecked(self, attributes: GuardedDict) -> None:
        super().__setattr__("_Operation__attributes", attributes)

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
        self.properties = GuardedDict(self, "properties", properties)
        self.attributes = GuardedDict(self, "attributes", attributes)
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
        record_direct_mutation_attempt("replace_operand", self, operand_index=index)
        old_value = self.operands[index]
        old_value.remove_use(self, index)
        operands = list(self.operands)
        operands[index] = value
        self.operands = tuple(operands)
        value.add_use(self, index)

    def erase_operand_uses(self) -> None:
        record_direct_mutation_attempt("erase_operand_uses", self)
        for index, value in enumerate(self.operands):
            value.remove_use(self, index)
