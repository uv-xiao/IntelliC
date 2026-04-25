from __future__ import annotations


class Context:
    """Registry for dialect-owned syntax classes."""

    def __init__(self) -> None:
        self._operations: dict[str, type] = {}
        self._types: dict[str, type] = {}
        self._attributes: dict[str, type] = {}

    def register_operation(self, name: str, op_type: type) -> None:
        if name in self._operations:
            raise ValueError(f"operation already registered: {name}")
        self._operations[name] = op_type

    def lookup_operation(self, name: str) -> type:
        try:
            return self._operations[name]
        except KeyError as exc:
            raise KeyError(f"unknown operation: {name}") from exc

    def register_type(self, name: str, type_cls: type) -> None:
        if name in self._types:
            raise ValueError(f"type already registered: {name}")
        self._types[name] = type_cls

    def register_attribute(self, name: str, attr_cls: type) -> None:
        if name in self._attributes:
            raise ValueError(f"attribute already registered: {name}")
        self._attributes[name] = attr_cls
