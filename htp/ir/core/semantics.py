from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

KERNEL_IR_SCHEMA_ID = "htp.kernel_ir.v1"
WORKLOAD_IR_SCHEMA_ID = "htp.workload_ir.v1"


@dataclass(frozen=True)
class KernelArg:
    name: str
    kind: str
    dtype: str
    shape: tuple[str, ...] = ()
    memory_space: str | None = None
    role: str | None = None
    alias_of: str | None = None
    source: str | None = None
    distribution: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class KernelOp:
    op_id: str
    entity_id: str
    op: str
    intrinsic: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    attrs: dict[str, Any]
    effects: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class KernelIR:
    entry: str
    args: tuple[KernelArg, ...]
    buffers: tuple[KernelArg, ...]
    ops: tuple[KernelOp, ...]


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


def kernel_arg_from_payload(payload: dict[str, Any]) -> KernelArg:
    return KernelArg(
        name=str(payload["name"]),
        kind=str(payload["kind"]),
        dtype=str(payload["dtype"]),
        shape=tuple(str(item) for item in payload.get("shape", ())),
        memory_space=str(payload["memory_space"]) if payload.get("memory_space") is not None else None,
        role=str(payload["role"]) if payload.get("role") is not None else None,
        alias_of=str(payload["alias_of"]) if payload.get("alias_of") is not None else None,
        source=str(payload["source"]) if payload.get("source") is not None else None,
        distribution=tuple(dict(item) for item in payload.get("distribution", ()) if isinstance(item, dict)),
    )


def kernel_op_from_payload(payload: dict[str, Any]) -> KernelOp:
    return KernelOp(
        op_id=str(payload["op_id"]),
        entity_id=str(payload.get("entity_id", "")),
        op=str(payload["op"]),
        intrinsic=str(payload.get("intrinsic", payload["op"])),
        inputs=tuple(str(item) for item in payload.get("inputs", ())),
        outputs=tuple(str(item) for item in payload.get("outputs", ())),
        attrs=dict(payload.get("attrs", {})),
        effects={
            str(key): tuple(str(item) for item in value)
            for key, value in dict(payload.get("effects", {})).items()
        },
    )


def kernel_ir_from_payload(payload: dict[str, Any]) -> KernelIR:
    return KernelIR(
        entry=str(payload.get("entry", "")),
        args=tuple(
            kernel_arg_from_payload(dict(item)) for item in payload.get("args", ()) if isinstance(item, dict)
        ),
        buffers=tuple(
            kernel_arg_from_payload(dict(item))
            for item in payload.get("buffers", ())
            if isinstance(item, dict)
        ),
        ops=tuple(
            kernel_op_from_payload(dict(item)) for item in payload.get("ops", ()) if isinstance(item, dict)
        ),
    )


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


def kernel_ir_payload(value: KernelIR) -> dict[str, Any]:
    if not value.entry and not value.args and not value.buffers and not value.ops:
        return {}
    return {"schema": KERNEL_IR_SCHEMA_ID, **to_payload(value)}


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


def to_payload(value: Any) -> Any:
    if is_dataclass(value):
        return to_payload(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_payload(item) for item in value]
    return value


__all__ = [
    "KernelArg",
    "KernelIR",
    "KernelOp",
    "KERNEL_IR_SCHEMA_ID",
    "WorkloadIR",
    "WorkloadTask",
    "kernel_arg_from_payload",
    "kernel_ir_from_payload",
    "kernel_ir_payload",
    "kernel_op_from_payload",
    "to_payload",
    "WORKLOAD_IR_SCHEMA_ID",
    "workload_ir_from_payload",
    "workload_ir_payload",
    "workload_task_from_payload",
]
