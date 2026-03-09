from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from htp.compiler_errors import compiler_error
from htp.intrinsics import get_intrinsic_decl
from htp.ir.layout import (
    DistributionFacet,
    HardwareFacet,
    LayoutFacetProduct,
    MemoryFacet,
    distribution_from_payload,
    distribution_matches,
    join_distribution_facets,
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
            distribution=tuple(
                {
                    "kind": str(item.get("kind", "replicate")),
                    **({"axis": str(item["axis"])} if item.get("axis") is not None else {}),
                }
                if isinstance(item, Mapping)
                else {"kind": str(item)}
                for item in argument.get("distribution", ())
            ),
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
    entry = str(kernel_ir.get("entry", workload_ir.get("entry", "")))
    types = {
        "schema": TYPES_SCHEMA_ID,
        "values": {},
        "buffers": {},
    }
    for index, argument in enumerate(kernel_ir.get("args", ())):
        name = str(argument["name"])
        if argument.get("kind") == "buffer":
            types["buffers"][name] = _buffer_type_payload(argument, memory_spaces)
        else:
            types["values"][name] = _value_type_payload(argument, entry=entry, index=index)
    layout = {
        "schema": LAYOUT_SCHEMA_ID,
        "target": dict(target),
        "memory_spaces": memory_spaces,
        "threading": _threading_for_backend(backend, kernel_ir),
        "tiling": _tiling_for_kernel(kernel_ir, backend),
        "facets": _layout_facets(memory_spaces, kernel_ir),
    }
    layout["joins"] = _layout_joins(kernel_ir, layout)
    layout["relayouts"] = _layout_relayouts(kernel_ir, layout)
    _validate_layout_contracts(kernel_ir, layout, entry=entry)
    protocols = _protocol_effects(workload_ir)
    tokens = _token_effects(kernel_ir)
    barriers = _barriers_for_kernel(kernel_ir, tokens=tokens)
    collectives = _collective_effects(kernel_ir, layout=layout)
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
        "intrinsics": _intrinsic_effect_contracts(kernel_ir),
        "barriers": barriers,
        "channels": _channel_effects(workload_ir, kernel_ir),
        "protocols": protocols,
        "tokens": tokens,
        "collectives": collectives,
    }
    _validate_effect_contracts(
        effects,
        entry=entry,
        kernel_ir=kernel_ir,
        workload_ir=workload_ir,
    )
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


def build_loop_dependencies(
    *,
    entry: str,
    kernel_ir: Mapping[str, Any],
) -> dict[str, Any]:
    last_writer: dict[str, str] = {}
    edges: list[dict[str, Any]] = []
    for op in kernel_ir.get("ops", ()):
        op_id = str(op["op_id"])
        for read_name in op.get("effects", {}).get("reads", ()):
            writer = last_writer.get(str(read_name))
            if writer is not None:
                edges.append(
                    {
                        "src": writer,
                        "dst": op_id,
                        "kind": "flow",
                        "buffer": str(read_name),
                    }
                )
        for write_name in op.get("effects", {}).get("writes", ()):
            last_writer[str(write_name)] = op_id
    return {
        "schema": "htp.analysis.loop_deps.v1",
        "entry": entry,
        "op_ids": [str(op["op_id"]) for op in kernel_ir.get("ops", ())],
        "edges": edges,
    }


def build_async_resource_checks(
    *,
    entry: str,
    kernel_ir: Mapping[str, Any],
    effects: Mapping[str, Any],
    workload_ir: Mapping[str, Any],
) -> dict[str, Any]:
    channel_protocols = [
        {
            "name": str(item.get("name", "")),
            "protocol": str(item.get("protocol", "fifo")),
            "capacity": int(item.get("capacity", 1) or 1),
            "participants": list(item.get("participants", ())),
            "deadlock_safe": bool(item.get("deadlock_safe", True)),
            "hazards": [dict(hazard) for hazard in item.get("hazards", ())],
        }
        for item in effects.get("protocols", ())
        if isinstance(item, Mapping)
    ]
    unresolved_tokens = [
        dict(item)
        for item in effects.get("tokens", ())
        if isinstance(item, Mapping) and str(item.get("status", "")) != "discharged"
    ]
    pending_collectives = [
        dict(item)
        for item in effects.get("collectives", ())
        if isinstance(item, Mapping) and str(item.get("status", "")) != "discharged"
    ]
    barrier_scopes = [
        {
            "barrier_id": str(item.get("barrier_id", "")),
            "scope": str(item.get("scope", "thread_block")),
            "kind": str(item.get("kind", "implicit")),
            "event_dependencies": list(item.get("event_dependencies", ())),
        }
        for item in effects.get("barriers", ())
        if isinstance(item, Mapping)
    ]
    return {
        "schema": "htp.analysis.async_resources.v1",
        "entry": entry,
        "tokens": list(effects.get("tokens", ())),
        "barriers": list(effects.get("barriers", ())),
        "channel_protocols": channel_protocols,
        "collectives": list(effects.get("collectives", ())),
        "unresolved_tokens": unresolved_tokens,
        "pending_collectives": pending_collectives,
        "barrier_scopes": barrier_scopes,
        "resource_summary": {
            "token_count": len(list(effects.get("tokens", ()))),
            "barrier_count": len(list(effects.get("barriers", ()))),
            "collective_count": len(list(effects.get("collectives", ()))),
            "pending_token_count": len(unresolved_tokens),
            "pending_collective_count": len(pending_collectives),
            "protocol_hazard_count": sum(len(item["hazards"]) for item in channel_protocols),
            "op_count": len(list(kernel_ir.get("ops", ()))),
        },
    }


def build_warp_role_plan(
    *,
    entry: str,
    kernel_ir: Mapping[str, Any],
    target: Mapping[str, str],
    schedule_directives: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    directives = _normalize_schedule_directives(schedule_directives or {})
    num_warps = int(directives.get("resources", {}).get("num_warps", 1) or 1)
    subgroup_kind = "warp" if target.get("backend") == "nvgpu" else "group"
    operator = str(directives.get("specialize", {}).get("operator", "generic"))
    compute_responsibility = "mma" if operator == "matmul" else operator
    if num_warps <= 1:
        roles = [{"name": "compute", "count": 1, "responsibilities": ["compute"]}]
        handoffs: list[dict[str, Any]] = []
    else:
        producer_count = min(2, max(1, num_warps // 2))
        consumer_count = max(1, num_warps - producer_count)
        roles = [
            {"name": "producer", "count": producer_count, "responsibilities": ["async_copy", "handoff"]},
            {
                "name": "consumer",
                "count": consumer_count,
                "responsibilities": [compute_responsibility, "accumulate"],
            },
        ]
        handoffs = [
            {
                "from": "producer",
                "to": "consumer",
                "buffer": "shared",
                "protocol": "barriered_pingpong",
            }
        ]
    return {
        "schema": "htp.analysis.warp_role_plan.v1",
        "entry": entry,
        "target": dict(target),
        "subgroup_kind": subgroup_kind,
        "roles": roles,
        "handoffs": handoffs,
        "anchors": {
            "op_ids": [str(op["op_id"]) for op in kernel_ir.get("ops", ())],
        },
    }


def apply_warp_role_plan(
    schedule: Mapping[str, Any],
    *,
    warp_role_plan: Mapping[str, Any],
) -> dict[str, Any]:
    next_schedule = dict(schedule)
    roles = [dict(role) for role in warp_role_plan.get("roles", ())]
    next_schedule["specialization"] = {
        "applied": True,
        "kind": "warp" if len(roles) > 1 else "single_role",
        "roles": roles,
        "handoff": dict(warp_role_plan.get("handoffs", [{}])[0]) if warp_role_plan.get("handoffs") else None,
    }
    next_schedule["warp_role_plan"] = {
        "kind": next_schedule["specialization"]["kind"],
        "roles": [str(role["name"]) for role in roles],
    }
    return next_schedule


def build_software_pipeline_plan(
    *,
    entry: str,
    schedule_plan: Mapping[str, Any],
    warp_role_plan: Mapping[str, Any],
    kernel_ir: Mapping[str, Any],
) -> dict[str, Any]:
    del warp_role_plan
    depth = int(schedule_plan.get("pipeline_depth", 1) or 1)
    buffering = str(schedule_plan.get("buffering_strategy", "single"))
    slots = [0] if depth <= 1 or buffering == "single" else [0, 1]
    return {
        "schema": "htp.analysis.pipeline_plan.v1",
        "entry": entry,
        "depth": depth,
        "buffering": buffering,
        "stages": ["prefetch", "compute", "drain"] if depth > 1 else ["compute"],
        "steady_state_slots": slots,
        "op_ids": [str(op["op_id"]) for op in kernel_ir.get("ops", ())],
    }


def apply_software_pipeline_plan(
    schedule: Mapping[str, Any],
    scheduled_ops: Sequence[Mapping[str, Any]],
    *,
    pipeline_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    slots = list(pipeline_plan.get("steady_state_slots", (0,))) or [0]
    stage_order = list(pipeline_plan.get("stages", ("compute",)))
    next_schedule = dict(schedule)
    next_schedule["software_pipeline"] = {
        "applied": True,
        "depth": int(pipeline_plan.get("depth", 1) or 1),
        "buffering": str(pipeline_plan.get("buffering", "single")),
        "steady_state_slots": slots,
        "stage_order": stage_order,
    }
    next_schedule["buffering_strategy"] = str(pipeline_plan.get("buffering", "single"))
    next_scheduled_ops: list[dict[str, Any]] = []
    for index, op in enumerate(scheduled_ops):
        next_op = dict(op)
        next_op["slot"] = slots[index % len(slots)]
        op_phase = str(next_op.get("phase", "compute"))
        next_op["pipeline_stage"] = (
            op_phase if op_phase in stage_order else stage_order[min(index, len(stage_order) - 1)]
        )
        next_scheduled_ops.append(next_op)
    return next_schedule, next_scheduled_ops


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
                **(
                    {
                        "distribution": [
                            dict(item) if isinstance(item, Mapping) else {"kind": str(item)}
                            for item in argument.get("distribution", ())
                        ]
                    }
                    if argument.get("distribution") is not None
                    else {}
                ),
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
            {
                "processes": [
                    {
                        **dict(item),
                        **(
                            {"steps": [dict(step) for step in item.get("steps", ())]}
                            if item.get("steps")
                            else {}
                        ),
                    }
                    for item in workload.get("processes", ())
                ]
            }
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
        "processes": [
            {
                **dict(item),
                **({"steps": [dict(step) for step in item.get("steps", ())]} if item.get("steps") else {}),
            }
            for item in processes
        ],
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
        "value",
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


def _value_type_payload(argument: Mapping[str, Any], *, entry: str, index: int) -> dict[str, Any]:
    kind = str(argument.get("kind", "scalar"))
    dtype = dtype_from_name(str(argument["dtype"]))
    shape = shape_from_sequence(list(argument.get("shape", ())))
    if kind == "view":
        alias_of = argument.get("alias_of")
        source = argument.get("source", alias_of)
        if alias_of is None or source is None:
            raise compiler_error(
                "HTP.TYPECHECK.UNKNOWN_ALIAS",
                f"view {argument.get('name')!r} requires alias_of/source metadata.",
                node_id=f"{entry}:Arg:{index}" if entry else None,
                entity_id=f"{entry}:E{index}" if entry else None,
                payload_ref_hint="semantic.types",
                fix_hints_ref="docs/design/features.md",
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
        distribution = distribution_from_payload(argument.get("distribution"), rank=len(shape))
        buffer_layouts[str(argument["name"])] = layout_to_payload(
            LayoutFacetProduct(
                distribution=distribution,
                memory=MemoryFacet(
                    space=str(memory_spaces.get(str(argument["name"]), "global")),
                    layout="row_major",
                    order=tuple(range(len(shape))),
                ),
                hardware=HardwareFacet(scope="thread_block", vector_width=1),
            )
        )
    return {"buffers": buffer_layouts}


def _distribution_for_buffer(layout: Mapping[str, Any], buffer_name: str) -> DistributionFacet:
    payload = layout.get("facets", {}).get("buffers", {}).get(buffer_name, {})
    distribution = payload.get("distribution", {}) if isinstance(payload, Mapping) else {}
    dims = distribution.get("dims", ()) if isinstance(distribution, Mapping) else ()
    return distribution_from_payload(list(dims), rank=len(list(dims)))


def _layout_joins(kernel_ir: Mapping[str, Any], layout: Mapping[str, Any]) -> list[dict[str, Any]]:
    joins: list[dict[str, Any]] = []
    for op in kernel_ir.get("ops", ()):
        op_name = str(op.get("op"))
        if op_name not in {"elementwise_binary", "matmul"}:
            continue
        lhs_name = str(op.get("inputs", [None])[0] or "")
        rhs_name = str(op.get("inputs", [None, None])[1] or "")
        out_name = str(op.get("outputs", [None])[0] or "")
        if not lhs_name or not rhs_name or not out_name:
            continue
        lhs = _distribution_for_buffer(layout, lhs_name)
        rhs = _distribution_for_buffer(layout, rhs_name)
        if op_name == "matmul":
            joined = _matmul_output_distribution(lhs, rhs)
        else:
            joined = join_distribution_facets(lhs, rhs)
        joins.append(
            {
                "op_id": str(op["op_id"]),
                "rule": op_name,
                "lhs": lhs_name,
                "rhs": rhs_name,
                "out": out_name,
                "ok": joined is not None,
                "joined": layout_to_payload(joined) if joined is not None else None,
            }
        )
    return joins


def _layout_relayouts(kernel_ir: Mapping[str, Any], layout: Mapping[str, Any]) -> list[dict[str, Any]]:
    relayouts: list[dict[str, Any]] = []
    for op in kernel_ir.get("ops", ()):
        if str(op.get("op")) != "relayout":
            continue
        source_name = str(op.get("inputs", [None])[0] or "")
        out_name = str(op.get("outputs", [None])[0] or "")
        relayouts.append(
            {
                "op_id": str(op["op_id"]),
                "source": source_name,
                "out": out_name,
                "source_distribution": layout_to_payload(_distribution_for_buffer(layout, source_name)),
                "out_distribution": layout_to_payload(_distribution_for_buffer(layout, out_name)),
            }
        )
    return relayouts


def _matmul_output_distribution(lhs: DistributionFacet, rhs: DistributionFacet) -> DistributionFacet | None:
    if len(lhs.dims) < 2 or len(rhs.dims) < 2:
        return None
    return DistributionFacet((lhs.dims[0], rhs.dims[1]))


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


def _barriers_for_kernel(
    kernel_ir: Mapping[str, Any], *, tokens: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    pending_tokens_by_scope: dict[str, list[str]] = {}
    for token in tokens:
        if str(token.get("status", "")) == "pending":
            pending_tokens_by_scope.setdefault(str(token.get("required_scope", "thread_block")), []).append(
                str(token.get("token_id", ""))
            )
    barriers: list[dict[str, Any]] = []
    for op in kernel_ir.get("ops", ()):
        op_id = str(op["op_id"])
        if str(op.get("intrinsic", "")) == "portable.barrier":
            scope = str(op.get("attrs", {}).get("scope", "thread_block"))
            event_dependencies = list(pending_tokens_by_scope.get(scope, ()))
            barriers.append(
                {
                    "barrier_id": f"{op_id}.barrier",
                    "after": op_id,
                    "reason": "explicit_barrier",
                    "scope": scope,
                    "kind": "explicit",
                    "discharges": ["memory.pending_copy", "token.async_copy"],
                    "event_dependencies": event_dependencies,
                }
            )
        elif get_op_spec(str(op.get("op"))).barrier_after:
            barriers.append(
                {
                    "barrier_id": f"{op_id}.barrier",
                    "after": op_id,
                    "reason": "pipeline_ready",
                    "scope": "thread_block",
                    "kind": "implicit",
                    "discharges": ["sync.barrier"],
                    "event_dependencies": [],
                }
            )
    return barriers


def _is_sharded_layout(payload: Mapping[str, Any]) -> bool:
    distribution = payload.get("distribution", {})
    dims = distribution.get("dims", ()) if isinstance(distribution, Mapping) else ()
    return any(
        isinstance(dim, Mapping) and str(dim.get("kind", "replicate")) not in {"replicate", "R"}
        for dim in dims
    )


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
    entry = str(workload_ir.get("entry", ""))
    for index, channel in enumerate(workload_ir.get("channels", ())):
        channel_name = str(channel["name"])
        participants = sorted(
            str(process.get("name", process.get("task_id", "")))
            for process in processes
            if any(str(item.get("channel")) == channel_name for item in process.get("puts", ()))
            or any(str(item.get("channel")) == channel_name for item in process.get("gets", ()))
        )
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
            "participants": participants,
        }
        if not balanced:
            raise compiler_error(
                "HTP.PROTOCOL.UNBALANCED_CHANNEL",
                f"channel {channel_name!r} has puts={puts} and gets={gets}.",
                node_id=f"{entry}:Channel:{index}" if entry else None,
                payload_ref_hint="semantic.workload_ir",
                fix_hints_ref="docs/design/impls/09_debuggability.md",
                channel=channel_name,
                puts=puts,
                gets=gets,
            )
        hazards = _protocol_hazards(channel_name, channel, processes)
        obligation["hazards"] = hazards
        obligation["deadlock_safe"] = not hazards
        if hazards:
            first_hazard = hazards[0]
            raise compiler_error(
                "HTP.PROTOCOL.DEADLOCK_RISK",
                f"channel {channel_name!r} has a potential deadlock hazard: {first_hazard['detail']}",
                node_id=f"{entry}:Channel:{index}" if entry else None,
                payload_ref_hint="semantic.workload_ir",
                fix_hints_ref="docs/design/impls/09_debuggability.md",
                channel=channel_name,
                hazard=first_hazard,
            )
        obligations.append(obligation)
    return obligations


def _process_steps(process: Mapping[str, Any]) -> list[dict[str, Any]]:
    explicit = [dict(item) for item in process.get("steps", ()) if isinstance(item, Mapping)]
    if explicit:
        return explicit
    return [
        *({"kind": "get", **dict(item)} for item in process.get("gets", ()) if isinstance(item, Mapping)),
        *({"kind": "put", **dict(item)} for item in process.get("puts", ()) if isinstance(item, Mapping)),
    ]


def _protocol_hazards(
    channel_name: str, channel: Mapping[str, Any], processes: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    hazards: list[dict[str, Any]] = []
    channel_processes = [
        process
        for process in processes
        if any(str(item.get("channel")) == channel_name for item in process.get("puts", ()))
        or any(str(item.get("channel")) == channel_name for item in process.get("gets", ()))
    ]
    first_steps = []
    for process in channel_processes:
        steps = _process_steps(process)
        if steps:
            first_steps.append(
                {
                    "process": str(process.get("name", process.get("task_id", ""))),
                    "step": dict(steps[0]),
                }
            )
    initial_puts = [
        item
        for item in first_steps
        if str(item["step"].get("kind")) == "put" and str(item["step"].get("channel")) == channel_name
    ]
    initial_gets = [
        item
        for item in first_steps
        if str(item["step"].get("kind")) == "get" and str(item["step"].get("channel")) == channel_name
    ]
    capacity = int(channel.get("capacity", 0) or 0)
    if initial_gets and not initial_puts and capacity <= 0:
        hazards.append(
            {
                "kind": "all_processes_block_on_empty_channel",
                "channel": channel_name,
                "participants": [item["process"] for item in initial_gets],
                "detail": "every participating process performs an initial get on an empty zero-capacity channel",
            }
        )
    wait_edges: list[dict[str, str]] = []
    process_by_name = {
        str(process.get("name", process.get("task_id", ""))): process for process in channel_processes
    }
    initial_producers_by_channel: dict[str, list[str]] = {}
    for item in first_steps:
        if str(item["step"].get("kind")) == "put":
            initial_producers_by_channel.setdefault(str(item["step"].get("channel", "")), []).append(
                item["process"]
            )
    for item in first_steps:
        if str(item["step"].get("kind")) != "get":
            continue
        src = item["process"]
        awaited_channel = str(item["step"].get("channel", ""))
        producers = initial_producers_by_channel.get(awaited_channel, ())
        for producer in producers:
            wait_edges.append({"src": src, "dst": producer})
    if wait_edges and _has_wait_cycle(wait_edges):
        hazards.append(
            {
                "kind": "initial_wait_cycle",
                "channel": channel_name,
                "participants": sorted(process_by_name),
                "detail": "initial blocking channel operations form a wait cycle across processes",
                "edges": wait_edges,
            }
        )
    return hazards


def _has_wait_cycle(edges: Sequence[Mapping[str, str]]) -> bool:
    graph: dict[str, set[str]] = {}
    for edge in edges:
        src = str(edge.get("src", ""))
        dst = str(edge.get("dst", ""))
        if src and dst:
            graph.setdefault(src, set()).add(dst)
    seen: set[str] = set()
    stack: set[str] = set()

    def visit(node: str) -> bool:
        if node in stack:
            return True
        if node in seen:
            return False
        seen.add(node)
        stack.add(node)
        for nxt in graph.get(node, ()):
            if visit(nxt):
                return True
        stack.remove(node)
        return False

    return any(visit(node) for node in graph)


def _token_effects(kernel_ir: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    pending_order: list[str] = []
    for op in kernel_ir.get("ops", ()):
        op_id = str(op["op_id"])
        intrinsic = str(op.get("intrinsic", ""))
        attrs = op.get("attrs", {})
        if intrinsic == "portable.async_copy":
            token_name = str(attrs.get("token", f"{op_id}.token"))
            event_id = f"{op_id}.event"
            records[token_name] = {
                "token_id": token_name,
                "token_kind": "async_copy",
                "produced_by": op_id,
                "required_scope": str(attrs.get("scope", "thread_block")),
                "source": attrs.get("source"),
                "target": attrs.get("target"),
                "event_id": event_id,
                "status": "pending",
                "discharged_by": None,
                "discharge_kind": None,
            }
            pending_order.append(token_name)
        elif intrinsic == "portable.await":
            token_name = str(attrs.get("token", pending_order[-1] if pending_order else ""))
            if token_name and token_name in records:
                records[token_name]["status"] = "discharged"
                records[token_name]["discharged_by"] = op_id
                records[token_name]["discharge_kind"] = "await"
                if token_name in pending_order:
                    pending_order.remove(token_name)
        elif intrinsic == "portable.barrier":
            scope = str(attrs.get("scope", "thread_block"))
            discharged = [
                token_name
                for token_name in list(pending_order)
                if str(records[token_name].get("required_scope", "thread_block")) == scope
            ]
            for token_name in discharged:
                records[token_name]["status"] = "discharged"
                records[token_name]["discharged_by"] = op_id
                records[token_name]["discharge_kind"] = "barrier"
                pending_order.remove(token_name)
    return list(records.values())


def _collective_effects(kernel_ir: Mapping[str, Any], *, layout: Mapping[str, Any]) -> list[dict[str, Any]]:
    required_outputs = _collective_requirements(kernel_ir, layout)
    records: list[dict[str, Any]] = []
    for op in kernel_ir.get("ops", ()):
        if str(op.get("intrinsic", "")) != "portable.allreduce":
            continue
        op_id = str(op["op_id"])
        outputs = [str(name) for name in op.get("outputs", ())]
        collective_id = f"{op_id}.collective"
        discharged = any(name in required_outputs for name in outputs)
        records.append(
            {
                "collective_id": collective_id,
                "op_id": op_id,
                "kind": "allreduce",
                "outputs": outputs,
                "status": "discharged" if discharged else "redundant",
                "discharged_by": op_id if discharged else None,
                "required_by": sorted(name for name in outputs if name in required_outputs),
                "discharge_rule": "allreduce_over_sharded_output" if discharged else "no_pending_obligation",
            }
        )
    for buffer_name in sorted(required_outputs):
        if any(buffer_name in record["required_by"] for record in records):
            continue
        records.append(
            {
                "collective_id": f"{buffer_name}.collective",
                "op_id": None,
                "kind": "allreduce",
                "outputs": [buffer_name],
                "status": "pending",
                "discharged_by": None,
                "required_by": [buffer_name],
                "discharge_rule": "allreduce_over_sharded_output",
            }
        )
    return records


def _collective_requirements(kernel_ir: Mapping[str, Any], layout: Mapping[str, Any]) -> set[str]:
    requirements: set[str] = set()
    for op in kernel_ir.get("ops", ()):
        op_name = str(op.get("op"))
        outputs = [str(name) for name in op.get("outputs", ())]
        if op_name == "matmul":
            lhs_name = str(op.get("inputs", [None])[0] or "")
            rhs_name = str(op.get("inputs", [None, None])[1] or "")
            lhs = _distribution_for_buffer(layout, lhs_name)
            rhs = _distribution_for_buffer(layout, rhs_name)
            if len(lhs.dims) >= 2 and str(lhs.dims[1].kind) == "shard":
                requirements.update(outputs)
            if len(rhs.dims) >= 1 and str(rhs.dims[0].kind) == "shard":
                requirements.update(outputs)
        elif op_name == "reduction_sum":
            source_name = str(op.get("inputs", [None])[0] or "")
            axis = int(op.get("attrs", {}).get("axis", 0) or 0)
            source = _distribution_for_buffer(layout, source_name)
            if len(source.dims) > axis and str(source.dims[axis].kind) == "shard":
                requirements.update(outputs)
    return requirements


def _intrinsic_effect_contracts(kernel_ir: Mapping[str, Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for op in kernel_ir.get("ops", ()):
        intrinsic = str(op.get("intrinsic", ""))
        decl = get_intrinsic_decl(intrinsic)
        payloads.append(
            {
                "op_id": str(op["op_id"]),
                "intrinsic": intrinsic,
                "requires_effects": list(decl.requires_effects),
                "produces_effects": list(decl.produces_effects),
                "discharges_effects": list(decl.discharges_effects),
            }
        )
    return payloads


def _validate_dtype_contracts(kernel_ir: Mapping[str, Any], *, target: Mapping[str, str]) -> None:
    backend = target["backend"]
    entry = str(kernel_ir.get("entry", ""))
    for index, argument in enumerate(kernel_ir.get("args", ())):
        if argument.get("kind") != "buffer":
            continue
        dtype = str(argument["dtype"])
        name = str(argument["name"])
        if backend == "nvgpu" and dtype != "f32":
            raise compiler_error(
                "HTP.TYPECHECK.UNSUPPORTED_BUFFER_DTYPE",
                f"nvgpu buffer {name!r} requires 'f32', got {dtype!r}.",
                node_id=f"{entry}:Arg:{index}" if entry else None,
                entity_id=f"{entry}:E{index}" if entry else None,
                payload_ref_hint="semantic.kernel_ir",
                fix_hints_ref="docs/design/features.md",
                backend=backend,
                manifest_value=dtype,
            )


def _validate_alias_contracts(kernel_ir: Mapping[str, Any]) -> None:
    entry = str(kernel_ir.get("entry", ""))
    aliasables = {
        str(argument["name"]): str(argument.get("kind", ""))
        for argument in kernel_ir.get("args", ())
        if str(argument.get("kind", "")) in {"buffer", "view"}
    }
    mutable_aliases: dict[str, list[str]] = {}
    for index, argument in enumerate(kernel_ir.get("args", ())):
        alias_of = argument.get("alias_of")
        if alias_of is None:
            continue
        alias_name = str(alias_of)
        if alias_name not in aliasables:
            raise compiler_error(
                "HTP.TYPECHECK.UNKNOWN_ALIAS",
                f"{argument.get('name')!r} aliases unknown value {alias_name!r}.",
                node_id=f"{entry}:Arg:{index}" if entry else None,
                entity_id=f"{entry}:E{index}" if entry else None,
                payload_ref_hint="semantic.kernel_ir",
                fix_hints_ref="docs/design/features.md",
                alias_of=alias_name,
            )
        role = str(argument.get("role") or "")
        if role in {"output", "temp"}:
            mutable_aliases.setdefault(alias_name, []).append(str(argument["name"]))
    for alias_name, users in mutable_aliases.items():
        if len(users) > 1:
            first_index = next(
                idx
                for idx, argument in enumerate(kernel_ir.get("args", ()))
                if str(argument.get("name")) in users
            )
            raise compiler_error(
                "HTP.TYPECHECK.ALIAS_WRITE_CONFLICT",
                f"alias base {alias_name!r} has multiple mutable aliases {users!r}.",
                node_id=f"{entry}:Arg:{first_index}" if entry else None,
                entity_id=f"{entry}:E{first_index}" if entry else None,
                payload_ref_hint="semantic.kernel_ir",
                fix_hints_ref="docs/design/features.md",
                alias_of=alias_name,
                mutable_aliases=users,
            )


def _validate_layout_contracts(
    kernel_ir: Mapping[str, Any], layout: Mapping[str, Any], *, entry: str
) -> None:
    for join in layout.get("joins", ()):
        if not bool(join.get("ok", False)):
            raise compiler_error(
                "HTP.LAYOUT.DISTRIBUTION_INCOMPATIBLE",
                (
                    f"op {join.get('op_id')!r} joins incompatible distributions for "
                    f"{join.get('lhs')!r} and {join.get('rhs')!r}."
                ),
                node_id=f"{entry}:{join.get('op_id')}" if entry else None,
                payload_ref_hint="semantic.layout",
                fix_hints_ref="docs/design/features.md",
                op_id=join.get("op_id"),
            )
        expected = join_distribution_facets(
            _distribution_for_buffer(layout, str(join.get("lhs", ""))),
            _distribution_for_buffer(layout, str(join.get("rhs", ""))),
        )
        if expected is None:
            continue
        out_distribution = _distribution_for_buffer(layout, str(join.get("out", "")))
        if not distribution_matches(out_distribution, expected):
            has_relayout = any(
                str(item.get("out", "")) == str(join.get("out", "")) for item in layout.get("relayouts", ())
            )
            if not has_relayout:
                raise compiler_error(
                    "HTP.LAYOUT.RELAYOUT_REQUIRED",
                    (f"op {join.get('op_id')!r} requires explicit relayout for output {join.get('out')!r}."),
                    node_id=f"{entry}:{join.get('op_id')}" if entry else None,
                    payload_ref_hint="semantic.layout",
                    fix_hints_ref="docs/design/features.md",
                    op_id=join.get("op_id"),
                    output=join.get("out"),
                )
    for relayout in layout.get("relayouts", ()):
        src_distribution = distribution_from_payload(
            relayout.get("source_distribution", {}).get("dims", ())
            if isinstance(relayout.get("source_distribution"), Mapping)
            else (),
            rank=len(relayout.get("source_distribution", {}).get("dims", ()))
            if isinstance(relayout.get("source_distribution"), Mapping)
            else 0,
        )
        out_distribution = distribution_from_payload(
            relayout.get("out_distribution", {}).get("dims", ())
            if isinstance(relayout.get("out_distribution"), Mapping)
            else (),
            rank=len(relayout.get("out_distribution", {}).get("dims", ()))
            if isinstance(relayout.get("out_distribution"), Mapping)
            else 0,
        )
        if distribution_matches(src_distribution, out_distribution):
            raise compiler_error(
                "HTP.LAYOUT.REDUNDANT_RELAYOUT",
                f"relayout op {relayout.get('op_id')!r} does not change distribution.",
                node_id=f"{entry}:{relayout.get('op_id')}" if entry else None,
                payload_ref_hint="semantic.layout",
                fix_hints_ref="docs/design/features.md",
                op_id=relayout.get("op_id"),
            )


def _validate_effect_contracts(
    effects: Mapping[str, Any],
    *,
    entry: str,
    kernel_ir: Mapping[str, Any],
    workload_ir: Mapping[str, Any],
) -> None:
    del kernel_ir, workload_ir
    pending_tokens = [
        dict(item)
        for item in effects.get("tokens", ())
        if isinstance(item, Mapping) and str(item.get("status", "")) != "discharged"
    ]
    if pending_tokens:
        first = pending_tokens[0]
        raise compiler_error(
            "HTP.EFFECT.UNDISCHARGED_TOKEN",
            f"token {first.get('token_id')!r} is not discharged by await or barrier.",
            node_id=str(first.get("produced_by", "")) or None,
            payload_ref_hint="semantic.effects",
            fix_hints_ref="docs/design/impls/09_debuggability.md",
            token=first.get("token_id"),
        )
    pending_collectives = [
        dict(item)
        for item in effects.get("collectives", ())
        if isinstance(item, Mapping) and str(item.get("status", "")) == "pending"
    ]
    if pending_collectives:
        first = pending_collectives[0]
        raise compiler_error(
            "HTP.EFFECT.UNDISCHARGED_COLLECTIVE",
            f"collective obligation for {first.get('required_by')} is still pending.",
            node_id=str(first.get("op_id", "")) or None,
            payload_ref_hint="semantic.effects",
            fix_hints_ref="docs/design/features.md",
            collective=first.get("collective_id"),
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
    "apply_software_pipeline_plan",
    "apply_warp_role_plan",
    "build_semantic_model",
    "build_schedule_plan",
    "build_software_pipeline_plan",
    "build_type_layout_effects",
    "build_warp_role_plan",
    "canonicalize_program",
    "normalize_target",
    "scheduled_ops_from_plan",
    "snapshot_program",
    "stage_payloads_from_program",
]
