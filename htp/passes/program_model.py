from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def normalize_target(program: Mapping[str, Any]) -> dict[str, str]:
    target = program.get("target")
    backend = "generic"
    option = "default"
    if isinstance(target, Mapping):
        if isinstance(target.get("backend"), str) and target["backend"]:
            backend = str(target["backend"])
        if isinstance(target.get("option"), str) and target["option"]:
            option = str(target["option"])
    return {"backend": backend, "option": option}


def canonicalize_ops(raw_ops: Sequence[object]) -> list[dict[str, Any]]:
    canonical_ops: list[dict[str, Any]] = []
    for index, raw_op in enumerate(raw_ops):
        if isinstance(raw_op, Mapping) and isinstance(raw_op.get("op"), str):
            kind = str(raw_op["op"])
        else:
            kind = str(raw_op)
        signature = _op_signature(kind)
        canonical_ops.append(
            {
                "op_id": f"op{index}",
                "op": kind,
                "phase": signature["phase"],
                "reads": list(signature["reads"]),
                "writes": list(signature["writes"]),
                "latency": signature["latency"],
                "barrier_after": signature["barrier_after"],
            }
        )
    return canonical_ops


def build_type_layout_effects(
    canonical_ops: Sequence[Mapping[str, Any]],
    *,
    target: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    backend = target["backend"]
    if backend == "pto":
        memory_spaces = {"input": "gm", "tile": "ub", "accum": "ub", "output": "gm"}
        threading = {"core": "aiv", "block_dim": 1}
    elif backend == "nvgpu":
        memory_spaces = {"input": "global", "tile": "shared", "accum": "register", "output": "global"}
        threading = {"thread_block": [128, 1, 1], "warp_group": 1}
    else:
        memory_spaces = {"input": "global", "tile": "local", "accum": "local", "output": "global"}
        threading = {"mode": "generic"}

    reads: dict[str, list[str]] = {}
    writes: dict[str, list[str]] = {}
    buffers: dict[str, str] = {}
    barriers: list[dict[str, str]] = []
    for op in canonical_ops:
        op_id = str(op["op_id"])
        reads[op_id] = [str(name) for name in op["reads"]]
        writes[op_id] = [str(name) for name in op["writes"]]
        for buffer_name in (*reads[op_id], *writes[op_id]):
            buffers.setdefault(buffer_name, _buffer_type(buffer_name))
        if op.get("barrier_after"):
            barriers.append({"after": op_id, "reason": "tile_ready"})

    types = {
        "buffers": buffers,
        "op_types": {
            str(op["op_id"]): {
                "reads": list(reads[str(op["op_id"])]),
                "writes": list(writes[str(op["op_id"])]),
            }
            for op in canonical_ops
        },
    }
    layout = {
        "target": dict(target),
        "tile_shape": [16, 16],
        "memory_spaces": memory_spaces,
        "threading": threading,
    }
    effects = {
        "reads": reads,
        "writes": writes,
        "barriers": barriers,
    }
    return types, layout, effects


def build_schedule_plan(
    *,
    entry: str,
    canonical_ops: Sequence[Mapping[str, Any]],
    effects: Mapping[str, Any],
    target: Mapping[str, str],
) -> dict[str, Any]:
    barrier_after = {
        str(item["after"]): str(item["reason"])
        for item in effects.get("barriers", ())
        if isinstance(item, Mapping) and "after" in item and "reason" in item
    }
    ticks: list[dict[str, Any]] = []
    tick_index = 0
    for op in canonical_ops:
        op_id = str(op["op_id"])
        ticks.append(
            {
                "tick": tick_index,
                "op_id": op_id,
                "op": str(op["op"]),
                "phase": str(op["phase"]),
                "reads": list(op["reads"]),
                "writes": list(op["writes"]),
                "latency": int(op["latency"]),
            }
        )
        tick_index += 1
        if op_id in barrier_after:
            ticks.append(
                {
                    "tick": tick_index,
                    "op_id": f"{op_id}.barrier",
                    "op": "barrier",
                    "phase": "sync",
                    "depends_on": op_id,
                    "reason": barrier_after[op_id],
                }
            )
            tick_index += 1

    return {
        "schema": "htp.analysis.schedule_plan.v1",
        "entry": entry,
        "target": dict(target),
        "pipeline_depth": max(1, sum(1 for op in canonical_ops if str(op["phase"]) == "compute")),
        "ticks": ticks,
    }


def scheduled_ops_from_plan(schedule_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    scheduled_ops: list[dict[str, Any]] = []
    for tick in schedule_plan.get("ticks", ()):
        if not isinstance(tick, Mapping):
            continue
        scheduled_ops.append(
            {
                "tick": int(tick["tick"]),
                "op_id": str(tick["op_id"]),
                "op": str(tick["op"]),
                "phase": str(tick["phase"]),
            }
        )
    return scheduled_ops


def _op_signature(kind: str) -> dict[str, object]:
    if kind in {"load", "load_tile"}:
        return {
            "phase": "producer",
            "reads": ("input",),
            "writes": ("tile",),
            "latency": 1,
            "barrier_after": True,
        }
    if kind in {"compute", "compute_tile", "mma"}:
        return {
            "phase": "compute",
            "reads": ("tile", "weights"),
            "writes": ("accum",),
            "latency": 2,
            "barrier_after": False,
        }
    if kind in {"store", "store_tile"}:
        return {
            "phase": "consumer",
            "reads": ("accum",),
            "writes": ("output",),
            "latency": 1,
            "barrier_after": False,
        }
    return {
        "phase": "custom",
        "reads": (),
        "writes": (),
        "latency": 1,
        "barrier_after": False,
    }


def _buffer_type(buffer_name: str) -> str:
    return {
        "input": "f32[16x16]",
        "tile": "f32[16x16]",
        "weights": "f32[16x16]",
        "accum": "f32[16x16]",
        "output": "f32[16x16]",
    }.get(buffer_name, "opaque")


__all__ = [
    "build_schedule_plan",
    "build_type_layout_effects",
    "canonicalize_ops",
    "normalize_target",
    "scheduled_ops_from_plan",
]
