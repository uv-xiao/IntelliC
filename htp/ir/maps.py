from __future__ import annotations

from dataclasses import dataclass

from htp.schemas import BINDING_MAP_SCHEMA_ID, ENTITY_MAP_SCHEMA_ID


@dataclass(frozen=True)
class RewriteRecord:
    before: str | None
    after: tuple[str, ...]
    reason: str
    origin: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "before": self.before,
            "after": list(self.after),
            "reason": self.reason,
        }
        if self.origin:
            payload["origin"] = list(self.origin)
        return payload


class _BaseMap:
    schema_id: str
    field_name: str

    def __init__(self, *, pass_id: str, stage_before: str, stage_after: str) -> None:
        self.pass_id = pass_id
        self.stage_before = stage_before
        self.stage_after = stage_after
        self._records: list[RewriteRecord] = []

    def record(
        self,
        *,
        before: str | None,
        after: list[str] | tuple[str, ...],
        reason: str,
        origin: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self._records.append(
            RewriteRecord(
                before=before,
                after=tuple(sorted(after)),
                reason=reason,
                origin=tuple(sorted(origin or ())),
            )
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema": self.schema_id,
            "pass_id": self.pass_id,
            "stage_before": self.stage_before,
            "stage_after": self.stage_after,
            self.field_name: [
                record.to_json()
                for record in sorted(
                    self._records,
                    key=lambda item: (item.before is None, item.before or "", item.after, item.reason, item.origin),
                )
            ],
        }


class EntityMap(_BaseMap):
    schema_id = ENTITY_MAP_SCHEMA_ID
    field_name = "entities"


class BindingMap(_BaseMap):
    schema_id = BINDING_MAP_SCHEMA_ID
    field_name = "bindings"


__all__ = ["BindingMap", "EntityMap", "RewriteRecord"]
