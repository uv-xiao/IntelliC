from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import Any

from .schema import RelationSchema


_next_record_id = count(1)


@dataclass(frozen=True)
class TraceRecord:
    id: int
    relation: str
    subject: object
    value: Any
    current: bool = True
    retracted_by: str | None = None


class TraceDB:
    """Append-only fact/event store with current and history projections."""

    def __init__(self) -> None:
        self._records: list[TraceRecord] = []

    def put(self, schema: RelationSchema | str, subject: object, value: Any) -> TraceRecord:
        relation = schema.name if isinstance(schema, RelationSchema) else schema
        record = TraceRecord(next(_next_record_id), relation, subject, value)
        self._records.append(record)
        return record

    def query(self, relation: str, subject: object | None = None) -> tuple[TraceRecord, ...]:
        return tuple(
            record
            for record in self._records
            if record.current
            and record.relation == relation
            and (subject is None or record.subject == subject)
        )

    def history(self, relation: str, subject: object | None = None) -> tuple[TraceRecord, ...]:
        return tuple(
            record
            for record in self._records
            if record.relation == relation and (subject is None or record.subject == subject)
        )

    def require(self, relation: str, subject: object) -> TraceRecord:
        records = self.query(relation, subject)
        if not records:
            raise KeyError(f"missing required fact {relation} for {subject}")
        return records[-1]

    def retract(self, record_id: int, reason: str) -> None:
        for index, record in enumerate(self._records):
            if record.id == record_id:
                self._records[index] = TraceRecord(
                    record.id,
                    record.relation,
                    record.subject,
                    record.value,
                    current=False,
                    retracted_by=reason,
                )
                return
        raise KeyError(f"unknown trace record: {record_id}")
