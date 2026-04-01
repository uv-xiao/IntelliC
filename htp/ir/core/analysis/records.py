from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnalysisRecord(Mapping[str, Any]):
    """Typed wrapper for committed-stage analysis payloads."""

    schema: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload = dict(self.fields)
        if self.schema is not None:
            payload = {"schema": self.schema, **payload}
        return payload

    def __getitem__(self, key: str) -> Any:
        return self.to_payload()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_payload())

    def __len__(self) -> int:
        return len(self.to_payload())


def analysis_record_from_payload(payload: Mapping[str, Any]) -> AnalysisRecord:
    schema = str(payload["schema"]) if payload.get("schema") is not None else None
    fields = {str(key): value for key, value in payload.items() if key != "schema"}
    return AnalysisRecord(schema=schema, fields=fields)


__all__ = ["AnalysisRecord", "analysis_record_from_payload"]
