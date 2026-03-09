from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAPPING_PLAN_SCHEMA_ID = "htp.analysis.aie_mapping_plan.v1"
FIFO_PLAN_SCHEMA_ID = "htp.analysis.aie_fifo_plan.v1"


def build_mapping_plan(state: Mapping[str, Any], *, profile: str) -> dict[str, Any]:
    workload_ir = state.get("workload_ir", {})
    layout = state.get("layout", {})
    tasks = list(workload_ir.get("tasks", ()))
    memory_spaces = dict(layout.get("memory_spaces", {}))
    tile_rows = max(1, len(tasks))
    tiles = [
        {
            "task_id": str(task["task_id"]),
            "kernel": str(task.get("kernel", "")),
            "coords": [0, index],
            "memory_space": "l2",
        }
        for index, task in enumerate(tasks)
    ]
    buffers = [
        {
            "name": str(buffer_name),
            "memory_space": str(space),
            "tile": [0, min(index, tile_rows - 1)] if tiles else [0, 0],
        }
        for index, (buffer_name, space) in enumerate(sorted(memory_spaces.items()))
    ]
    return {
        "schema": MAPPING_PLAN_SCHEMA_ID,
        "entry": str(state.get("entry", "")),
        "profile": profile,
        "tiles": tiles,
        "buffers": buffers,
    }


def build_fifo_plan(state: Mapping[str, Any]) -> dict[str, Any]:
    workload_ir = state.get("workload_ir", {})
    processes = [dict(item) for item in workload_ir.get("processes", ())]
    channels = []
    for channel in workload_ir.get("channels", ()):
        name = str(channel["name"])
        producers = [
            {
                "process": str(process.get("name", process.get("task_id", ""))),
                "task_id": str(process.get("task_id", "")),
                "count": int(item.get("count", 1) or 1),
            }
            for process in processes
            for item in process.get("puts", ())
            if str(item.get("channel")) == name
        ]
        consumers = [
            {
                "process": str(process.get("name", process.get("task_id", ""))),
                "task_id": str(process.get("task_id", "")),
                "count": int(item.get("count", 1) or 1),
            }
            for process in processes
            for item in process.get("gets", ())
            if str(item.get("channel")) == name
        ]
        channels.append(
            {
                "name": name,
                "dtype": str(channel.get("dtype", "")),
                "capacity": int(channel.get("capacity", 0) or 0),
                "protocol": str(channel.get("protocol", "fifo")),
                "kind": str(channel.get("kind", "fifo")),
                "producers": producers,
                "consumers": consumers,
            }
        )
    return {
        "schema": FIFO_PLAN_SCHEMA_ID,
        "entry": str(state.get("entry", "")),
        "channels": channels,
    }


__all__ = [
    "FIFO_PLAN_SCHEMA_ID",
    "MAPPING_PLAN_SCHEMA_ID",
    "build_fifo_plan",
    "build_mapping_plan",
]
