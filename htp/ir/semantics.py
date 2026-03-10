from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


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
    "WorkloadIR",
    "WorkloadTask",
    "to_payload",
]
