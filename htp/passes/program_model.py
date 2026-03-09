from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from htp.ir.layout import (
    DistributionFacet,
    DistributionPlacement,
    HardwareFacet,
    LayoutFacetProduct,
    MemoryFacet,
    layout_to_payload,
)
from htp.ir.op_specs import get_op_spec, op_effects
from htp.ir.semantics import KernelArg, KernelIR, KernelOp, WorkloadIR, WorkloadTask, to_payload
from htp.ir.types import (
    BufferType,
    ChannelType,
    TensorType,
    TileType,
    TokenType,
    ViewType,
    dtype_from_name,
    shape_from_sequence,
    type_to_payload,
)
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
    schedule_directives: dict[str, Any] = {}
    if isinstance(program.get("wsp"), Mapping):
        workload = dict(program["wsp"].get("workload", {}))
        schedule_directives = _normalize_schedule_directives(program["wsp"].get("schedule", {}))
    elif isinstance(program.get("csp"), Mapping):
        workload = _lower_csp_surface(entry, program["csp"], kernel)
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
        "schedule_directives": schedule_directives,
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
            alias_of=str(argument["alias_of"]) if argument.get("alias_of") is not None else None,
            source=str(argument["source"]) if argument.get("source") is not None else None,
        )
        for argument in kernel.get("args", ())
    )
    buffers = tuple(argument for argument in args if argument.kind == "buffer")
    ops = tuple(
        KernelOp(
            op_id=f"op{index}",
            entity_id=f"{entry}:E{len(args) + index}",
            op=str(op["op"]),
            intrinsic=get_op_spec(str(op["op"])).intrinsic,
            inputs=_op_inputs(op),
            outputs=_op_outputs(op),
            attrs=_op_attrs(op),
            effects=op_effects(str(op["op"]), dict(op)),
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
        processes=tuple(dict(item) for item in workload.get("processes", ())),
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
    _validate_dtype_contracts(kernel_ir, target=target)
    memory_spaces = _memory_spaces_for_backend(backend, kernel_ir)
    _validate_alias_contracts(kernel_ir)
    types = {
        "schema": TYPES_SCHEMA_ID,
        "values": {
            str(argument["name"]): _value_type_payload(argument)
            for argument in kernel_ir.get("args", ())
            if argument.get("kind") != "buffer"
        },
        "buffers": {
            str(argument["name"]): _buffer_type_payload(argument, memory_spaces)
            for argument in kernel_ir.get("args", ())
            if argument.get("kind") == "buffer"
        },
    }
    layout = {
        "schema": LAYOUT_SCHEMA_ID,
        "target": dict(target),
        "memory_spaces": memory_spaces,
        "threading": _threading_for_backend(backend, kernel_ir),
        "tiling": _tiling_for_kernel(kernel_ir, backend),
        "facets": _layout_facets(memory_spaces, kernel_ir),
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
        "channels": _channel_effects(workload_ir, kernel_ir),
        "protocols": _protocol_effects(workload_ir),
        "tokens": _token_effects(kernel_ir),
        "collectives": _collective_effects(kernel_ir),
    }
    return types, layout, effects


def build_schedule_plan(
    *,
    entry: str,
    kernel_ir: Mapping[str, Any],
    effects: Mapping[str, Any],
    target: Mapping[str, str],
    schedule_directives: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    barrier_after = {
        str(item["after"]): str(item["reason"])
        for item in effects.get("barriers", ())
        if isinstance(item, Mapping) and "after" in item and "reason" in item
    }
    directives = _normalize_schedule_directives(schedule_directives or {})
    legality = _schedule_legality(target, directives)
    ticks: list[dict[str, Any]] = []
    tick_index = 0
    for op in kernel_ir.get("ops", ()):
        op_id = str(op["op_id"])
        ticks.append(
            {
                "tick": tick_index,
                "op_id": op_id,
                "op": str(op["op"]),
                "intrinsic": str(op.get("intrinsic", get_op_spec(str(op["op"])).intrinsic)),
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
            int(directives.get("pipeline", {}).get("depth", 0) or 0),
            1,
            sum(1 for op in kernel_ir.get("ops", ()) if _phase_for_op(str(op["op"])) == "compute"),
        ),
        "directives": directives,
        "buffering_strategy": directives.get("pipeline", {}).get("buffering", "single"),
        "launch": {
            "grid": directives.get("bind", {}).get("grid", "grid"),
            "lane": directives.get("bind", {}).get("lane", "thread"),
            "num_warps": int(directives.get("resources", {}).get("num_warps", 1) or 1),
        },
        "warp_role_plan": {
            "kind": "single_role"
            if int(directives.get("resources", {}).get("num_warps", 1) or 1) <= 1
            else "split_roles",
            "roles": ["compute"],
        },
        "legality": legality,
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
                "intrinsic": str(tick.get("intrinsic", get_op_spec(str(tick["op"])).intrinsic)),
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
                "alias_of": str(argument["alias_of"]) if argument.get("alias_of") is not None else None,
                "source": str(argument["source"]) if argument.get("source") is not None else None,
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
    task_ids = {
        str(task["task_id"])
        for task in workload.get("tasks", ())
        if isinstance(task, Mapping) and "task_id" in task
    }
    normalized_dependencies = []
    for dependency in workload.get("dependencies", ()):
        dep = dict(dependency)
        src = str(dep.get("src", ""))
        dst = str(dep.get("dst", ""))
        if src not in task_ids or dst not in task_ids:
            raise ValueError(
                f"HTP.WORKLOAD.UNKNOWN_TASK: dependency {src!r}->{dst!r} references unknown task."
            )
        normalized_dependencies.append(dep)
    normalized_channels = []
    for channel in workload.get("channels", ()):
        channel_payload = dict(channel)
        if not isinstance(channel_payload.get("name"), str) or not channel_payload["name"]:
            raise ValueError("HTP.WORKLOAD.INVALID_CHANNEL: channels require a non-empty string name.")
        if not isinstance(channel_payload.get("dtype"), str) or not channel_payload["dtype"]:
            raise ValueError("HTP.WORKLOAD.INVALID_CHANNEL: channels require a non-empty string dtype.")
        channel_payload.setdefault("kind", "fifo")
        normalized_channels.append(channel_payload)
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
        "channels": normalized_channels,
        "dependencies": normalized_dependencies,
        "kernel": str(kernel.get("name", entry)),
        **(
            {"processes": [dict(item) for item in workload.get("processes", ())]}
            if workload.get("processes")
            else {}
        ),
    }


def _lower_csp_surface(entry: str, csp: Mapping[str, Any], kernel: object) -> dict[str, Any]:
    kernel_name = str(kernel.get("name", entry)) if isinstance(kernel, Mapping) else entry
    processes = [dict(item) for item in csp.get("processes", ())]
    tasks = [
        {
            "task_id": str(item["task_id"]),
            "kind": "process",
            "kernel": str(item.get("kernel", kernel_name)),
            "args": [str(arg) for arg in item.get("args", ())],
        }
        for item in processes
    ]
    return {
        "entry": entry,
        "tasks": tasks,
        "channels": [dict(item) for item in csp.get("channels", ())],
        "dependencies": [],
        "kernel": kernel_name,
        "processes": processes,
    }


def _normalize_schedule_directives(schedule: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "tile": dict(schedule.get("tile", {})) if isinstance(schedule.get("tile"), Mapping) else {},
        "bind": dict(schedule.get("bind", {})) if isinstance(schedule.get("bind"), Mapping) else {},
        "pipeline": dict(schedule.get("pipeline", {}))
        if isinstance(schedule.get("pipeline"), Mapping)
        else {},
        "resources": dict(schedule.get("resources", {}))
        if isinstance(schedule.get("resources"), Mapping)
        else {},
        "specialize": dict(schedule.get("specialize", {}))
        if isinstance(schedule.get("specialize"), Mapping)
        else {},
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
    effects = op_effects(str(op.get("op")), dict(op))
    if effects["reads"]:
        return effects["reads"]
    return tuple(str(name) for name in op.get("inputs", ()))


def _op_outputs(op: Mapping[str, Any]) -> tuple[str, ...]:
    effects = op_effects(str(op.get("op")), dict(op))
    if effects["writes"]:
        return effects["writes"]
    return tuple(str(name) for name in op.get("outputs", ()))


def _op_attrs(op: Mapping[str, Any]) -> dict[str, Any]:
    reserved = {
        "op",
        "lhs",
        "rhs",
        "out",
        "inputs",
        "outputs",
        "source",
        "target",
        "value",
        "token",
        "channel",
    }
    return {str(key): value for key, value in op.items() if key not in reserved}


def _buffer_type_payload(argument: Mapping[str, Any], memory_spaces: Mapping[str, str]) -> dict[str, Any]:
    name = str(argument["name"])
    return type_to_payload(
        BufferType(
            dtype=dtype_from_name(str(argument["dtype"])),
            shape=shape_from_sequence(list(argument.get("shape", ()))),
            space=str(memory_spaces.get(name, "global")),
            alias_of=str(argument["alias_of"]) if argument.get("alias_of") is not None else None,
        )
    )


def _value_type_payload(argument: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(argument.get("kind", "scalar"))
    dtype = dtype_from_name(str(argument["dtype"]))
    shape = shape_from_sequence(list(argument.get("shape", ())))
    if kind == "view":
        alias_of = argument.get("alias_of")
        source = argument.get("source", alias_of)
        if alias_of is None or source is None:
            raise ValueError(
                f"HTP.TYPECHECK.UNKNOWN_ALIAS: view {argument.get('name')!r} requires alias_of/source metadata."
            )
        return type_to_payload(ViewType(dtype=dtype, shape=shape, source=str(source), alias_of=str(alias_of)))
    if kind == "tensor":
        return type_to_payload(TensorType(dtype=dtype, shape=shape))
    if kind == "tile":
        return type_to_payload(TileType(dtype=dtype, shape=shape))
    if kind == "channel":
        capacity = argument.get("capacity")
        return type_to_payload(
            ChannelType(
                element=dtype,
                capacity=int(capacity) if capacity is not None else None,
                protocol=str(argument.get("protocol", "fifo")),
            )
        )
    if kind in {"async_token", "token"}:
        return type_to_payload(TokenType(token_kind=str(argument.get("token_kind", "async"))))
    return type_to_payload(dtype)


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


def _layout_facets(memory_spaces: Mapping[str, str], kernel_ir: Mapping[str, Any]) -> dict[str, Any]:
    buffer_layouts: dict[str, Any] = {}
    for argument in kernel_ir.get("args", ()):
        if argument.get("kind") != "buffer":
            continue
        shape = list(argument.get("shape", ()))
        buffer_layouts[str(argument["name"])] = layout_to_payload(
            LayoutFacetProduct(
                distribution=DistributionFacet(tuple(DistributionPlacement(kind="replicate") for _ in shape)),
                memory=MemoryFacet(
                    space=str(memory_spaces.get(str(argument["name"]), "global")),
                    layout="row_major",
                    order=tuple(range(len(shape))),
                ),
                hardware=HardwareFacet(scope="thread_block", vector_width=1),
            )
        )
    return {"buffers": buffer_layouts}


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
        if get_op_spec(str(op.get("op"))).barrier_after:
            barriers.append({"after": str(op["op_id"]), "reason": "pipeline_ready"})
    return barriers


def _phase_for_op(kind: str) -> str:
    return get_op_spec(kind).phase


def _latency_for_op(kind: str) -> int:
    return get_op_spec(kind).latency


def _channel_effects(workload_ir: Mapping[str, Any], kernel_ir: Mapping[str, Any]) -> list[dict[str, Any]]:
    channel_records = []
    for channel in workload_ir.get("channels", ()):
        name = str(channel["name"])
        producers = [
            str(op["op_id"])
            for op in kernel_ir.get("ops", ())
            if name in op.get("effects", {}).get("channel_writes", ())
        ]
        consumers = [
            str(op["op_id"])
            for op in kernel_ir.get("ops", ())
            if name in op.get("effects", {}).get("channel_reads", ())
        ]
        channel_records.append(
            {
                "name": name,
                "dtype": str(channel["dtype"]),
                "kind": str(channel.get("kind", "fifo")),
                "producers": producers,
                "consumers": consumers,
                **({"capacity": channel.get("capacity")} if channel.get("capacity") is not None else {}),
            }
        )
    return channel_records


def _protocol_effects(workload_ir: Mapping[str, Any]) -> list[dict[str, Any]]:
    processes = [dict(item) for item in workload_ir.get("processes", ())]
    obligations: list[dict[str, Any]] = []
    for channel in workload_ir.get("channels", ()):
        channel_name = str(channel["name"])
        puts = sum(
            int(item.get("count", 1))
            for process in processes
            for item in process.get("puts", ())
            if str(item.get("channel")) == channel_name
        )
        gets = sum(
            int(item.get("count", 1))
            for process in processes
            for item in process.get("gets", ())
            if str(item.get("channel")) == channel_name
        )
        balanced = puts == gets
        obligation = {
            "channel": channel_name,
            "protocol": str(channel.get("protocol", "fifo")),
            "capacity": int(channel.get("capacity", 0) or 0),
            "puts": puts,
            "gets": gets,
            "balanced": balanced,
        }
        if not balanced:
            raise ValueError(
                f"HTP.PROTOCOL.UNBALANCED_CHANNEL: channel {channel_name!r} has puts={puts} and gets={gets}."
            )
        obligations.append(obligation)
    return obligations


def _token_effects(kernel_ir: Mapping[str, Any]) -> list[dict[str, Any]]:
    tokens = []
    for op in kernel_ir.get("ops", ()):
        intrinsic = str(op.get("intrinsic", ""))
        if intrinsic == "portable.async_copy":
            tokens.append({"op_id": str(op["op_id"]), "token_kind": "async_copy", "status": "produced"})
        if intrinsic == "portable.await":
            tokens.append({"op_id": str(op["op_id"]), "token_kind": "async_copy", "status": "awaited"})
    return tokens


def _collective_effects(kernel_ir: Mapping[str, Any]) -> list[dict[str, Any]]:
    collectives = []
    for op in kernel_ir.get("ops", ()):
        if str(op.get("intrinsic", "")) == "portable.allreduce":
            collectives.append({"op_id": str(op["op_id"]), "kind": "allreduce", "status": "pending"})
    return collectives


def _validate_dtype_contracts(kernel_ir: Mapping[str, Any], *, target: Mapping[str, str]) -> None:
    backend = target["backend"]
    for argument in kernel_ir.get("args", ()):
        if argument.get("kind") != "buffer":
            continue
        dtype = str(argument["dtype"])
        name = str(argument["name"])
        if backend == "nvgpu" and dtype != "f32":
            raise ValueError(
                f"HTP.TYPECHECK.UNSUPPORTED_BUFFER_DTYPE: nvgpu buffer {name!r} requires 'f32', got {dtype!r}."
            )


def _validate_alias_contracts(kernel_ir: Mapping[str, Any]) -> None:
    aliasables = {
        str(argument["name"]): str(argument.get("kind", ""))
        for argument in kernel_ir.get("args", ())
        if str(argument.get("kind", "")) in {"buffer", "view"}
    }
    mutable_aliases: dict[str, list[str]] = {}
    for argument in kernel_ir.get("args", ()):
        alias_of = argument.get("alias_of")
        if alias_of is None:
            continue
        alias_name = str(alias_of)
        if alias_name not in aliasables:
            raise ValueError(
                f"HTP.TYPECHECK.UNKNOWN_ALIAS: {argument.get('name')!r} aliases unknown value {alias_name!r}."
            )
        role = str(argument.get("role") or "")
        if role in {"output", "temp"}:
            mutable_aliases.setdefault(alias_name, []).append(str(argument["name"]))
    for alias_name, users in mutable_aliases.items():
        if len(users) > 1:
            raise ValueError(
                f"HTP.TYPECHECK.ALIAS_WRITE_CONFLICT: alias base {alias_name!r} has multiple mutable aliases {users!r}."
            )


def _schedule_legality(target: Mapping[str, str], directives: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    num_warps = int(directives.get("resources", {}).get("num_warps", 1) or 1)
    if target.get("backend") == "nvgpu" and num_warps > 8:
        reasons.append("num_warps exceeds supported NV-GPU limit (8)")
    pipeline_depth = int(directives.get("pipeline", {}).get("depth", 1) or 1)
    if pipeline_depth < 1:
        reasons.append("pipeline depth must be >= 1")
    return {"ok": not reasons, "reasons": reasons}


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
    return {
        "schema": WORKLOAD_IR_SCHEMA_ID,
        "entry": "",
        "tasks": [],
        "channels": [],
        "dependencies": [],
        "processes": [],
    }


def _default_types() -> dict[str, Any]:
    return {"schema": TYPES_SCHEMA_ID, "values": {}, "buffers": {}}


def _default_layout() -> dict[str, Any]:
    return {
        "schema": LAYOUT_SCHEMA_ID,
        "memory_spaces": {},
        "threading": {},
        "tiling": {},
        "facets": {"buffers": {}},
    }


def _default_effects() -> dict[str, Any]:
    return {
        "schema": EFFECTS_SCHEMA_ID,
        "reads": {},
        "writes": {},
        "barriers": [],
        "channels": [],
        "protocols": [],
        "tokens": [],
        "collectives": [],
    }


def _default_schedule() -> dict[str, Any]:
    return {
        "schema": SCHEDULE_SCHEMA_ID,
        "ticks": [],
        "ordered_ops": [],
        "pipeline_depth": 0,
        "directives": {},
        "buffering_strategy": "single",
        "launch": {},
        "warp_role_plan": {"kind": "single_role", "roles": []},
        "legality": {"ok": True, "reasons": []},
    }


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
