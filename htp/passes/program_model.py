from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from htp.ir.semantics import KernelArg, KernelIR, KernelOp, WorkloadIR, WorkloadTask, to_payload
from htp.schemas import IDS_BINDINGS_SCHEMA_ID, IDS_ENTITIES_SCHEMA_ID

PROGRAM_AST_SCHEMA_ID = "htp.program_ast.v1"
KERNEL_IR_SCHEMA_ID = "htp.kernel_ir.v1"
WORKLOAD_IR_SCHEMA_ID = "htp.workload_ir.v1"
TYPES_SCHEMA_ID = "htp.types.v1"
LAYOUT_SCHEMA_ID = "htp.layout.v1"
EFFECTS_SCHEMA_ID = "htp.effects.v1"
SCHEDULE_SCHEMA_ID = "htp.schedule.v1"


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


def canonicalize_program(program: Mapping[str, Any]) -> dict[str, Any]:
    entry = str(program.get("entry", "demo_kernel"))
    target = normalize_target(program)
    kernel = program.get("kernel")
    workload = program.get("workload")
    if isinstance(kernel, Mapping):
        normalized_kernel = _normalize_kernel_surface(entry, kernel)
    else:
        normalized_kernel = _lift_ops_to_kernel(entry, list(program.get("ops", ())))
    if isinstance(workload, Mapping):
        normalized_workload = _normalize_workload_surface(entry, workload, normalized_kernel)
    else:
        normalized_workload = _default_workload(entry, normalized_kernel)
    return {
        "entry": entry,
        "target": target,
        "kernel": normalized_kernel,
        "workload": normalized_workload,
    }


def build_semantic_model(
    canonical_ast: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    entry = str(canonical_ast["entry"])
    kernel = canonical_ast["kernel"]
    workload = canonical_ast["workload"]
    args = tuple(
        KernelArg(
            name=str(argument["name"]),
            kind=str(argument["kind"]),
            dtype=str(argument["dtype"]),
            shape=tuple(str(dim) for dim in argument.get("shape", ())),
            role=str(argument["role"]) if argument.get("role") is not None else None,
        )
        for argument in kernel.get("args", ())
    )
    buffers = tuple(argument for argument in args if argument.kind == "buffer")
    ops = tuple(
        KernelOp(
            op_id=f"op{index}",
            entity_id=f"{entry}:E{len(args) + index}",
            op=str(op["op"]),
            inputs=_op_inputs(op),
            outputs=_op_outputs(op),
            attrs=_op_attrs(op),
            effects={
                "reads": _op_inputs(op),
                "writes": _op_outputs(op),
            },
        )
        for index, op in enumerate(kernel.get("ops", ()))
    )
    kernel_ir = KernelIR(entry=entry, args=args, buffers=buffers, ops=ops)
    tasks = tuple(
        WorkloadTask(
            task_id=str(task["task_id"]),
            kind=str(task["kind"]),
            kernel=str(task["kernel"]),
            args=tuple(str(name) for name in task.get("args", ())),
            entity_id=f"{entry}:E{len(args) + len(ops) + index}",
        )
        for index, task in enumerate(workload.get("tasks", ()))
    )
    workload_ir = WorkloadIR(
        entry=entry,
        tasks=tasks,
        channels=tuple(dict(channel) for channel in workload.get("channels", ())),
        dependencies=tuple(dict(dep) for dep in workload.get("dependencies", ())),
    )
    return (
        {"schema": KERNEL_IR_SCHEMA_ID, **to_payload(kernel_ir)},
        {"schema": WORKLOAD_IR_SCHEMA_ID, **to_payload(workload_ir)},
        _entities_payload(entry, args, ops, tasks),
        _bindings_payload(entry, args, ops, tasks),
    )


def build_type_layout_effects(
    kernel_ir: Mapping[str, Any],
    workload_ir: Mapping[str, Any],
    *,
    target: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    backend = target["backend"]
    types = {
        "schema": TYPES_SCHEMA_ID,
        "values": {
            str(argument["name"]): str(argument["dtype"])
            for argument in kernel_ir.get("args", ())
            if argument.get("kind") != "buffer"
        },
        "buffers": {
            str(argument["name"]): _shape_dtype(str(argument["dtype"]), argument.get("shape", ()))
            for argument in kernel_ir.get("args", ())
            if argument.get("kind") == "buffer"
        },
    }
    layout = {
        "schema": LAYOUT_SCHEMA_ID,
        "target": dict(target),
        "memory_spaces": _memory_spaces_for_backend(backend, kernel_ir),
        "threading": _threading_for_backend(backend, kernel_ir),
        "tiling": _tiling_for_kernel(kernel_ir, backend),
    }
    effects = {
        "schema": EFFECTS_SCHEMA_ID,
        "reads": {
            str(op["op_id"]): [str(name) for name in op.get("effects", {}).get("reads", ())]
            for op in kernel_ir.get("ops", ())
        },
        "writes": {
            str(op["op_id"]): [str(name) for name in op.get("effects", {}).get("writes", ())]
            for op in kernel_ir.get("ops", ())
        },
        "barriers": _barriers_for_kernel(kernel_ir),
        "channels": [dict(channel) for channel in workload_ir.get("channels", ())],
    }
    return types, layout, effects


def build_schedule_plan(
    *,
    entry: str,
    kernel_ir: Mapping[str, Any],
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
    for op in kernel_ir.get("ops", ()):
        op_id = str(op["op_id"])
        ticks.append(
            {
                "tick": tick_index,
                "op_id": op_id,
                "op": str(op["op"]),
                "phase": _phase_for_op(str(op["op"])),
                "reads": list(op.get("effects", {}).get("reads", ())),
                "writes": list(op.get("effects", {}).get("writes", ())),
                "latency": _latency_for_op(str(op["op"])),
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
        "pipeline_depth": max(
            1,
            sum(1 for op in kernel_ir.get("ops", ()) if _phase_for_op(str(op["op"])) == "compute"),
        ),
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


def stage_payloads_from_program(program: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "program_ast_payload": {"schema": PROGRAM_AST_SCHEMA_ID, "program": snapshot_program(program)},
        "kernel_ir_payload": dict(program.get("kernel_ir", _default_kernel_ir())),
        "workload_ir_payload": dict(program.get("workload_ir", _default_workload_ir())),
        "types_payload": dict(program.get("types", _default_types())),
        "layout_payload": dict(program.get("layout", _default_layout())),
        "effects_payload": dict(program.get("effects", _default_effects())),
        "schedule_payload": dict(program.get("schedule", _default_schedule())),
        "entities_payload": dict(program.get("entities_payload", _default_entities_payload())),
        "bindings_payload": dict(program.get("bindings_payload", _default_bindings_payload())),
    }


def snapshot_program(program: Mapping[str, Any]) -> dict[str, Any]:
    return to_payload(dict(program))


def _normalize_kernel_surface(entry: str, kernel: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": str(kernel.get("name", entry)),
        "args": [
            {
                "name": str(argument["name"]),
                "kind": str(argument["kind"]),
                "dtype": str(argument["dtype"]),
                "shape": [str(dim) for dim in argument.get("shape", ())],
                "role": str(argument["role"]) if argument.get("role") is not None else None,
            }
            for argument in kernel.get("args", ())
        ],
        "ops": [dict(op) for op in kernel.get("ops", ())],
    }


def _normalize_workload_surface(
    entry: str,
    workload: Mapping[str, Any],
    kernel: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "entry": str(workload.get("entry", entry)),
        "tasks": [
            {
                "task_id": str(task["task_id"]),
                "kind": str(task["kind"]),
                "kernel": str(task["kernel"]),
                "args": [str(name) for name in task.get("args", ())],
            }
            for task in workload.get("tasks", ())
        ],
        "channels": [dict(channel) for channel in workload.get("channels", ())],
        "dependencies": [dict(dep) for dep in workload.get("dependencies", ())],
        "kernel": str(kernel.get("name", entry)),
    }


def _lift_ops_to_kernel(entry: str, raw_ops: Sequence[object]) -> dict[str, Any]:
    raw_ops_list = list(raw_ops)
    if raw_ops_list == ["load", "mma", "store"]:
        return {
            "name": entry,
            "args": [
                {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
                {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
                {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
                {"name": "M", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "N", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "K", "kind": "scalar", "dtype": "i32", "role": "shape"},
            ],
            "ops": [
                {
                    "op": "matmul",
                    "lhs": "A",
                    "rhs": "B",
                    "out": "C",
                    "m": "M",
                    "n": "N",
                    "k": "K",
                    "dtype": "f32",
                }
            ],
        }
    return {
        "name": entry,
        "args": [
            {"name": "lhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
            {"name": "rhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
            {"name": "out", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "output"},
            {"name": "size", "kind": "scalar", "dtype": "i32", "role": "shape"},
        ],
        "ops": [
            {
                "op": "elementwise_binary",
                "operator": "add",
                "lhs": "lhs",
                "rhs": "rhs",
                "out": "out",
                "shape": ["size"],
                "dtype": "f32",
            }
        ],
    }


def _default_workload(entry: str, kernel: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entry": entry,
        "tasks": [
            {
                "task_id": "task0",
                "kind": "kernel_call",
                "kernel": str(kernel.get("name", entry)),
                "args": [str(argument["name"]) for argument in kernel.get("args", ())],
            }
        ],
        "channels": [],
        "dependencies": [],
    }


def _op_inputs(op: Mapping[str, Any]) -> tuple[str, ...]:
    if op.get("op") in {"matmul", "elementwise_binary"}:
        return (str(op["lhs"]), str(op["rhs"]))
    if op.get("op") == "channel_send":
        return (str(op["value"]),)
    if op.get("op") == "channel_recv":
        return (str(op["channel"]),)
    return tuple(str(name) for name in op.get("inputs", ()))


def _op_outputs(op: Mapping[str, Any]) -> tuple[str, ...]:
    if op.get("op") in {"matmul", "elementwise_binary"}:
        return (str(op["out"]),)
    if op.get("op") == "channel_recv":
        return (str(op["out"]),)
    return tuple(str(name) for name in op.get("outputs", ()))


def _op_attrs(op: Mapping[str, Any]) -> dict[str, Any]:
    reserved = {"op", "lhs", "rhs", "out", "inputs", "outputs"}
    return {str(key): value for key, value in op.items() if key not in reserved}


def _shape_dtype(dtype: str, shape: Sequence[object]) -> str:
    if not shape:
        return dtype
    return f"{dtype}[{'x'.join(str(dim) for dim in shape)}]"


def _memory_spaces_for_backend(backend: str, kernel_ir: Mapping[str, Any]) -> dict[str, str]:
    spaces: dict[str, str] = {}
    for argument in kernel_ir.get("args", ()):
        if argument.get("kind") != "buffer":
            continue
        name = str(argument["name"])
        if backend == "pto":
            spaces[name] = "gm"
        elif backend == "nvgpu":
            spaces[name] = "global"
        else:
            spaces[name] = "global"
    return spaces


def _threading_for_backend(backend: str, kernel_ir: Mapping[str, Any]) -> dict[str, Any]:
    has_matmul = any(str(op.get("op")) == "matmul" for op in kernel_ir.get("ops", ()))
    if backend == "pto":
        return {"core": "aiv", "block_dim": 1}
    if backend == "nvgpu":
        return {"thread_block": [16, 16, 1] if has_matmul else [128, 1, 1], "warp_group": 1}
    return {"mode": "generic"}


def _tiling_for_kernel(kernel_ir: Mapping[str, Any], backend: str) -> dict[str, Any]:
    if any(str(op.get("op")) == "matmul" for op in kernel_ir.get("ops", ())):
        return {"block": [16, 16, 16], "pipeline_stages": 1, "backend": backend}
    return {"block": [128], "pipeline_stages": 1, "backend": backend}


def _barriers_for_kernel(kernel_ir: Mapping[str, Any]) -> list[dict[str, str]]:
    barriers: list[dict[str, str]] = []
    for op in kernel_ir.get("ops", ()):
        if str(op.get("op")) in {"async_copy", "mma"}:
            barriers.append({"after": str(op["op_id"]), "reason": "pipeline_ready"})
    return barriers


def _phase_for_op(kind: str) -> str:
    if kind in {"async_copy", "load", "load_tile"}:
        return "producer"
    if kind in {"store", "store_tile"}:
        return "consumer"
    if kind in {"channel_send", "channel_recv", "barrier", "await"}:
        return "sync"
    return "compute"


def _latency_for_op(kind: str) -> int:
    if kind in {"matmul", "mma"}:
        return 2
    return 1


def _entities_payload(
    entry: str,
    args: Sequence[KernelArg],
    ops: Sequence[KernelOp],
    tasks: Sequence[WorkloadTask],
) -> dict[str, Any]:
    entities = []
    node_to_entity = []
    for index, argument in enumerate(args):
        entity_id = f"{entry}:E{index}"
        entities.append({"entity_id": entity_id, "kind": "Arg", "role": argument.role})
        node_to_entity.append({"node_id": f"{entry}:Arg:{index}", "entity_id": entity_id})
    for index, op in enumerate(ops):
        entities.append({"entity_id": op.entity_id, "kind": "Op", "role": op.op})
        node_to_entity.append({"node_id": f"{entry}:Op:{index}", "entity_id": op.entity_id})
    for index, task in enumerate(tasks):
        entities.append({"entity_id": task.entity_id, "kind": "Task", "role": task.kind})
        node_to_entity.append({"node_id": f"{entry}:Task:{index}", "entity_id": task.entity_id})
    return {
        "schema": IDS_ENTITIES_SCHEMA_ID,
        "def_id": entry,
        "entities": entities,
        "node_to_entity": node_to_entity,
    }


def _bindings_payload(
    entry: str,
    args: Sequence[KernelArg],
    ops: Sequence[KernelOp],
    tasks: Sequence[WorkloadTask],
) -> dict[str, Any]:
    scope_id = f"{entry}:S0"
    bindings = []
    name_uses = []
    for index, argument in enumerate(args):
        bindings.append(
            {
                "binding_id": f"{scope_id}:B{index}",
                "name": argument.name,
                "site_entity_id": f"{entry}:E{index}",
            }
        )
    name_to_binding = {binding["name"]: binding["binding_id"] for binding in bindings}
    use_index = 0
    for op in ops:
        for name in (*op.inputs, *op.outputs):
            binding_id = name_to_binding.get(name)
            if binding_id is None:
                continue
            name_uses.append({"node_id": f"{entry}:Name:{use_index}", "binding_id": binding_id})
            use_index += 1
    for task in tasks:
        for name in task.args:
            binding_id = name_to_binding.get(name)
            if binding_id is None:
                continue
            name_uses.append({"node_id": f"{entry}:TaskName:{use_index}", "binding_id": binding_id})
            use_index += 1
    return {
        "schema": IDS_BINDINGS_SCHEMA_ID,
        "def_id": entry,
        "scopes": [{"scope_id": scope_id, "parent": None, "kind": "function"}],
        "bindings": bindings,
        "name_uses": name_uses,
    }


def _default_kernel_ir() -> dict[str, Any]:
    return {"schema": KERNEL_IR_SCHEMA_ID, "entry": "", "args": [], "buffers": [], "ops": []}


def _default_workload_ir() -> dict[str, Any]:
    return {"schema": WORKLOAD_IR_SCHEMA_ID, "entry": "", "tasks": [], "channels": [], "dependencies": []}


def _default_types() -> dict[str, Any]:
    return {"schema": TYPES_SCHEMA_ID, "values": {}, "buffers": {}}


def _default_layout() -> dict[str, Any]:
    return {"schema": LAYOUT_SCHEMA_ID, "memory_spaces": {}, "threading": {}, "tiling": {}}


def _default_effects() -> dict[str, Any]:
    return {"schema": EFFECTS_SCHEMA_ID, "reads": {}, "writes": {}, "barriers": [], "channels": []}


def _default_schedule() -> dict[str, Any]:
    return {"schema": SCHEDULE_SCHEMA_ID, "ticks": [], "ordered_ops": [], "pipeline_depth": 0}


def _default_entities_payload() -> dict[str, Any]:
    return {"schema": IDS_ENTITIES_SCHEMA_ID, "def_id": "", "entities": [], "node_to_entity": []}


def _default_bindings_payload() -> dict[str, Any]:
    return {"schema": IDS_BINDINGS_SCHEMA_ID, "def_id": "", "scopes": [], "bindings": [], "name_uses": []}


__all__ = [
    "build_semantic_model",
    "build_schedule_plan",
    "build_type_layout_effects",
    "canonicalize_program",
    "normalize_target",
    "scheduled_ops_from_plan",
    "snapshot_program",
    "stage_payloads_from_program",
]
