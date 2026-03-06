from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityRecord:
    entity_id: str
    kind: str
    role: str | None = None

    def to_json(self) -> dict[str, str]:
        payload = {
            "entity_id": self.entity_id,
            "kind": self.kind,
        }
        if self.role is not None:
            payload["role"] = self.role
        return payload


@dataclass(frozen=True)
class NodeEntityRecord:
    node_id: str
    entity_id: str

    def to_json(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "entity_id": self.entity_id,
        }


@dataclass(frozen=True)
class ScopeRecord:
    scope_id: str
    parent: str | None
    kind: str

    def to_json(self) -> dict[str, str | None]:
        return {
            "scope_id": self.scope_id,
            "parent": self.parent,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class BindingRecord:
    binding_id: str
    name: str
    site_entity_id: str | None = None

    def to_json(self) -> dict[str, str | None]:
        payload = {
            "binding_id": self.binding_id,
            "name": self.name,
        }
        if self.site_entity_id is not None:
            payload["site_entity_id"] = self.site_entity_id
        return payload


@dataclass(frozen=True)
class NameUseRecord:
    node_id: str
    binding_id: str

    def to_json(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "binding_id": self.binding_id,
        }


__all__ = [
    "BindingRecord",
    "EntityRecord",
    "NameUseRecord",
    "NodeEntityRecord",
    "ScopeRecord",
]
