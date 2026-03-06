from __future__ import annotations

from htp.schemas import IDS_BINDINGS_SCHEMA_ID, IDS_ENTITIES_SCHEMA_ID

from .state import BindingRecord, EntityRecord, NameUseRecord, NodeEntityRecord, ScopeRecord


def node_id(def_id: str, kind: str, ordinal: int) -> str:
    return f"{def_id}:{kind}:{ordinal}"


def entity_id(def_id: str, ordinal: int) -> str:
    return f"{def_id}:E{ordinal}"


def scope_id(def_id: str, ordinal: int) -> str:
    return f"{def_id}:S{ordinal}"


def binding_id(scope: str, ordinal: int) -> str:
    return f"{scope}:B{ordinal}"


class EntityRegistry:
    def __init__(self, def_id: str) -> None:
        self.def_id = def_id
        self._entities: list[EntityRecord] = []
        self._node_links: list[NodeEntityRecord] = []

    def add(
        self,
        kind: str,
        *,
        role: str | None = None,
        node_kind: str | None = None,
        node_ordinal: int | None = None,
    ) -> str:
        next_entity_id = entity_id(self.def_id, len(self._entities))
        self._entities.append(EntityRecord(entity_id=next_entity_id, kind=kind, role=role))
        if node_kind is not None and node_ordinal is not None:
            self._node_links.append(
                NodeEntityRecord(
                    node_id=node_id(self.def_id, node_kind, node_ordinal),
                    entity_id=next_entity_id,
                )
            )
        return next_entity_id

    def to_json(self) -> dict[str, object]:
        return {
            "schema": IDS_ENTITIES_SCHEMA_ID,
            "def_id": self.def_id,
            "entities": [record.to_json() for record in sorted(self._entities, key=lambda item: item.entity_id)],
            "node_to_entity": [
                record.to_json()
                for record in sorted(self._node_links, key=lambda item: (item.node_id, item.entity_id))
            ],
        }


class BindingRegistry:
    def __init__(self, def_id: str) -> None:
        self.def_id = def_id
        self._scopes: list[ScopeRecord] = []
        self._bindings: list[BindingRecord] = []
        self._name_uses: list[NameUseRecord] = []
        self._binding_counts: dict[str, int] = {}

    def add_scope(self, kind: str, *, parent: str | None = None) -> str:
        next_scope_id = scope_id(self.def_id, len(self._scopes))
        self._scopes.append(ScopeRecord(scope_id=next_scope_id, parent=parent, kind=kind))
        self._binding_counts[next_scope_id] = 0
        return next_scope_id

    def add_binding(self, scope: str, name: str, *, site_entity_id: str | None = None) -> str:
        if scope not in self._binding_counts:
            raise ValueError(f"Unknown scope: {scope}")

        ordinal = self._binding_counts[scope]
        self._binding_counts[scope] = ordinal + 1
        next_binding_id = binding_id(scope, ordinal)
        self._bindings.append(
            BindingRecord(binding_id=next_binding_id, name=name, site_entity_id=site_entity_id)
        )
        return next_binding_id

    def add_name_use(self, kind: str, ordinal: int, binding: str) -> None:
        self._name_uses.append(
            NameUseRecord(
                node_id=node_id(self.def_id, kind, ordinal),
                binding_id=binding,
            )
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema": IDS_BINDINGS_SCHEMA_ID,
            "def_id": self.def_id,
            "scopes": [record.to_json() for record in sorted(self._scopes, key=lambda item: item.scope_id)],
            "bindings": [record.to_json() for record in sorted(self._bindings, key=lambda item: item.binding_id)],
            "name_uses": [
                record.to_json()
                for record in sorted(self._name_uses, key=lambda item: (item.node_id, item.binding_id))
            ],
        }


__all__ = [
    "BindingRegistry",
    "EntityRegistry",
    "binding_id",
    "entity_id",
    "node_id",
    "scope_id",
]
