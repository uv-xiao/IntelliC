from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class _IdentityPayload(Mapping[str, Any]):
    schema: str
    extras: dict[str, Any] = field(default_factory=dict)

    def _core_payload(self) -> dict[str, Any]:
        return {"schema": self.schema}

    def to_payload(self) -> dict[str, Any]:
        payload = self._core_payload()
        payload.update(self.extras)
        if _is_structurally_empty(payload):
            return {}
        return payload

    def __getitem__(self, key: str) -> Any:
        return self.to_payload()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_payload())

    def __len__(self) -> int:
        return len(self.to_payload())


@dataclass(frozen=True)
class EntityTable(_IdentityPayload):
    def_id: str = ""
    entities: tuple[dict[str, Any], ...] = ()
    node_to_entity: tuple[dict[str, Any], ...] = ()

    def _core_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "def_id": self.def_id,
            "entities": [dict(item) for item in self.entities],
            "node_to_entity": [dict(item) for item in self.node_to_entity],
        }


@dataclass(frozen=True)
class BindingTable(_IdentityPayload):
    def_id: str = ""
    scopes: tuple[dict[str, Any], ...] = ()
    bindings: tuple[dict[str, Any], ...] = ()
    name_uses: tuple[dict[str, Any], ...] = ()

    def _core_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "def_id": self.def_id,
            "scopes": [dict(item) for item in self.scopes],
            "bindings": [dict(item) for item in self.bindings],
            "name_uses": [dict(item) for item in self.name_uses],
        }


@dataclass(frozen=True)
class RewriteMap(_IdentityPayload):
    records_key: str = "records"
    records: tuple[dict[str, Any], ...] = ()
    pass_id: str | None = None
    stage_before: str | None = None
    stage_after: str | None = None

    def _core_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            self.records_key: [dict(item) for item in self.records],
        }
        if self.pass_id is not None:
            payload["pass_id"] = self.pass_id
        if self.stage_before is not None:
            payload["stage_before"] = self.stage_before
        if self.stage_after is not None:
            payload["stage_after"] = self.stage_after
        return payload


def entities_from_payload(payload: Mapping[str, Any]) -> EntityTable:
    extras = {
        str(key): value
        for key, value in payload.items()
        if key not in {"schema", "def_id", "entities", "node_to_entity"}
    }
    return EntityTable(
        schema=str(payload.get("schema", "htp.ids.entities.v1")),
        def_id=str(payload.get("def_id", "")),
        entities=tuple(dict(item) for item in payload.get("entities", ()) if isinstance(item, Mapping)),
        node_to_entity=tuple(
            dict(item) for item in payload.get("node_to_entity", ()) if isinstance(item, Mapping)
        ),
        extras=extras,
    )


def bindings_from_payload(payload: Mapping[str, Any]) -> BindingTable:
    extras = {
        str(key): value
        for key, value in payload.items()
        if key not in {"schema", "def_id", "scopes", "bindings", "name_uses"}
    }
    return BindingTable(
        schema=str(payload.get("schema", "htp.ids.bindings.v1")),
        def_id=str(payload.get("def_id", "")),
        scopes=tuple(dict(item) for item in payload.get("scopes", ()) if isinstance(item, Mapping)),
        bindings=tuple(dict(item) for item in payload.get("bindings", ()) if isinstance(item, Mapping)),
        name_uses=tuple(dict(item) for item in payload.get("name_uses", ()) if isinstance(item, Mapping)),
        extras=extras,
    )


def rewrite_map_from_payload(payload: Mapping[str, Any], *, default_schema: str) -> RewriteMap:
    records_key = next(
        (
            str(key)
            for key, value in payload.items()
            if key not in {"schema", "pass_id", "stage_before", "stage_after"} and isinstance(value, list)
        ),
        "records",
    )
    extras = {
        str(key): value
        for key, value in payload.items()
        if key not in {"schema", "pass_id", "stage_before", "stage_after", records_key}
    }
    return RewriteMap(
        schema=str(payload.get("schema", default_schema)),
        records_key=records_key,
        records=tuple(dict(item) for item in payload.get(records_key, ()) if isinstance(item, Mapping)),
        pass_id=str(payload["pass_id"]) if payload.get("pass_id") is not None else None,
        stage_before=str(payload["stage_before"]) if payload.get("stage_before") is not None else None,
        stage_after=str(payload["stage_after"]) if payload.get("stage_after") is not None else None,
        extras=extras,
    )


def _is_structurally_empty(payload: Mapping[str, Any]) -> bool:
    for key, value in payload.items():
        if key in {"schema", "def_id"} and value in {"", None}:
            continue
        if key == "schema":
            continue
        if value not in ({}, [], (), 0, None, ""):
            return False
    return True


__all__ = [
    "BindingTable",
    "EntityTable",
    "RewriteMap",
    "bindings_from_payload",
    "entities_from_payload",
    "rewrite_map_from_payload",
]
