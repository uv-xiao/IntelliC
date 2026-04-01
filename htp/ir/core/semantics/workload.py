from __future__ import annotations

from collections.abc import Mapping, Sequence
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
class WorkloadChannel:
    name: str
    dtype: str
    capacity: int
    protocol: str = "fifo"

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "capacity": self.capacity,
            "protocol": self.protocol,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> WorkloadChannel:
        return cls(
            name=str(payload["name"]),
            dtype=str(payload["dtype"]),
            capacity=int(payload["capacity"]),
            protocol=str(payload.get("protocol", "fifo")),
        )


@dataclass(frozen=True)
class WorkloadDependency:
    src: str
    dst: str

    def to_payload(self) -> dict[str, str]:
        return {"src": self.src, "dst": self.dst}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> WorkloadDependency:
        return cls(src=str(payload["src"]), dst=str(payload["dst"]))


@dataclass(frozen=True)
class WorkloadProcessStep:
    kind: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"kind": self.kind, **dict(self.attrs)}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> WorkloadProcessStep:
        return cls(
            kind=str(payload["kind"]),
            attrs={key: value for key, value in payload.items() if key != "kind"},
        )


@dataclass(frozen=True)
class WorkloadProcess:
    name: str
    task_id: str
    kernel: str
    args: tuple[str, ...]
    role: str | None = None
    steps: tuple[WorkloadProcessStep, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "task_id": self.task_id,
            "kernel": self.kernel,
            "args": list(self.args),
        }
        if self.role is not None:
            payload["role"] = self.role
        if self.steps:
            payload["steps"] = [step.to_payload() for step in self.steps]
            payload["puts"] = [
                step.to_payload() for step in self.steps if step.kind == "put"
            ]
            payload["gets"] = [
                step.to_payload() for step in self.steps if step.kind == "get"
            ]
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> WorkloadProcess:
        return cls(
            name=str(payload["name"]),
            task_id=str(payload["task_id"]),
            kernel=str(payload["kernel"]),
            args=tuple(str(item) for item in payload.get("args", ())),
            role=str(payload["role"]) if payload.get("role") is not None else None,
            steps=tuple(process_steps_from_payload(payload.get("steps", ()))),
        )


@dataclass(frozen=True)
class WorkloadIR:
    entry: str
    tasks: tuple[WorkloadTask, ...]
    channels: tuple[WorkloadChannel, ...] = ()
    dependencies: tuple[WorkloadDependency, ...] = ()
    processes: tuple[WorkloadProcess, ...] = ()
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


def workload_channel_from_payload(payload: dict[str, Any]) -> WorkloadChannel:
    return WorkloadChannel.from_payload(payload)


def workload_dependency_from_payload(payload: dict[str, Any]) -> WorkloadDependency:
    return WorkloadDependency.from_payload(payload)


def process_steps_from_payload(payload: Sequence[Any]) -> tuple[WorkloadProcessStep, ...]:
    steps: list[WorkloadProcessStep] = []
    for item in payload:
        if isinstance(item, WorkloadProcessStep):
            steps.append(item)
        elif isinstance(item, Mapping):
            steps.append(WorkloadProcessStep.from_payload(item))
    return tuple(steps)


def workload_process_from_payload(payload: dict[str, Any]) -> WorkloadProcess:
    steps = process_steps_from_payload(payload.get("steps", ()))
    if not steps:
        steps = process_steps_from_payload((*payload.get("gets", ()), *payload.get("puts", ())))
    return WorkloadProcess.from_payload({**payload, "steps": steps})


def workload_ir_from_payload(payload: dict[str, Any]) -> WorkloadIR:
    return WorkloadIR(
        entry=str(payload.get("entry", "")),
        tasks=tuple(
            workload_task_from_payload(dict(item))
            for item in payload.get("tasks", ())
            if isinstance(item, dict)
        ),
        channels=tuple(
            workload_channel_from_payload(dict(item))
            for item in payload.get("channels", ())
            if isinstance(item, dict)
        ),
        dependencies=tuple(
            workload_dependency_from_payload(dict(item))
            for item in payload.get("dependencies", ())
            if isinstance(item, dict)
        ),
        processes=tuple(
            workload_process_from_payload(dict(item))
            for item in payload.get("processes", ())
            if isinstance(item, dict)
        ),
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
    payload = {
        "schema": WORKLOAD_IR_SCHEMA_ID,
        "entry": value.entry,
        "tasks": [to_payload(task) for task in value.tasks],
        "channels": [channel.to_payload() for channel in value.channels],
        "dependencies": [dependency.to_payload() for dependency in value.dependencies],
        "processes": [process.to_payload() for process in value.processes],
        "routine": None if value.routine is None else dict(value.routine),
    }
    for task in payload.get("tasks", ()):
        if isinstance(task, dict) and task.get("attrs") == {}:
            task.pop("attrs", None)
    for process in payload.get("processes", ()):
        if isinstance(process, dict):
            if process.get("steps") == []:
                process.pop("steps", None)
            if process.get("puts") == []:
                process.pop("puts", None)
            if process.get("gets") == []:
                process.pop("gets", None)
    if payload.get("routine") is None:
        payload.pop("routine", None)
    return payload


__all__ = [
    "WORKLOAD_IR_SCHEMA_ID",
    "WorkloadChannel",
    "WorkloadDependency",
    "WorkloadIR",
    "WorkloadProcess",
    "WorkloadProcessStep",
    "WorkloadTask",
    "process_steps_from_payload",
    "workload_channel_from_payload",
    "workload_dependency_from_payload",
    "workload_ir_from_payload",
    "workload_ir_payload",
    "workload_process_from_payload",
    "workload_task_from_payload",
]
