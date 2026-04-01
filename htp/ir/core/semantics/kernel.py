from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .payloads import to_payload

KERNEL_IR_SCHEMA_ID = "htp.kernel_ir.v1"


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


def kernel_ir_payload(value: KernelIR) -> dict[str, Any]:
    if not value.entry and not value.args and not value.buffers and not value.ops:
        return {}
    return {"schema": KERNEL_IR_SCHEMA_ID, **to_payload(value)}


__all__ = [
    "KERNEL_IR_SCHEMA_ID",
    "KernelArg",
    "KernelIR",
    "KernelOp",
    "kernel_arg_from_payload",
    "kernel_ir_from_payload",
    "kernel_ir_payload",
    "kernel_op_from_payload",
]
