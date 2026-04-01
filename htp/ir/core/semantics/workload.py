from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .payloads import to_payload

WORKLOAD_IR_SCHEMA_ID = "htp.workload_ir.v1"


@dataclass(frozen=True)
class WorkloadTask:
    task_id: str
    kind: str
    kernel: str
    args: tuple[str, ...]
    entity_id: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkloadIR:
    entry: str
    tasks: tuple[WorkloadTask, ...]
    channels: tuple[dict[str, Any], ...]
    dependencies: tuple[dict[str, Any], ...]
    processes: tuple[dict[str, Any], ...] = ()
    routine: dict[str, Any] | None = None


def workload_task_from_payload(payload: dict[str, Any]) -> WorkloadTask:
    return WorkloadTask(
        task_id=str(payload["task_id"]),
        kind=str(payload["kind"]),
        kernel=str(payload["kernel"]),
        args=tuple(str(item) for item in payload.get("args", ())),
        entity_id=str(payload.get("entity_id", "")),
        attrs=dict(payload.get("attrs", {})),
    )


def workload_ir_from_payload(payload: dict[str, Any]) -> WorkloadIR:
    return WorkloadIR(
        entry=str(payload.get("entry", "")),
        tasks=tuple(
            workload_task_from_payload(dict(item))
            for item in payload.get("tasks", ())
            if isinstance(item, dict)
        ),
        channels=tuple(dict(item) for item in payload.get("channels", ()) if isinstance(item, dict)),
        dependencies=tuple(dict(item) for item in payload.get("dependencies", ()) if isinstance(item, dict)),
        processes=tuple(dict(item) for item in payload.get("processes", ()) if isinstance(item, dict)),
        routine=dict(payload["routine"]) if isinstance(payload.get("routine"), dict) else None,
    )


def workload_ir_payload(value: WorkloadIR) -> dict[str, Any]:
    if (
        not value.entry
        and not value.tasks
        and not value.channels
        and not value.dependencies
        and not value.processes
        and value.routine is None
    ):
        return {}
    payload = {"schema": WORKLOAD_IR_SCHEMA_ID, **to_payload(value)}
    for task in payload.get("tasks", ()):
        if isinstance(task, dict) and task.get("attrs") == {}:
            task.pop("attrs", None)
    if payload.get("routine") is None:
        payload.pop("routine", None)
    return payload


__all__ = [
    "WORKLOAD_IR_SCHEMA_ID",
    "WorkloadIR",
    "WorkloadTask",
    "workload_ir_from_payload",
    "workload_ir_payload",
    "workload_task_from_payload",
]
