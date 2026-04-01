from __future__ import annotations

from typing import Any

from .aspects import EffectsAspect, LayoutAspect, ScheduleAspect, TypesAspect
from .dialects import dialect_activation_payload
from .module import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems, ProgramModule
from .node_exec import NODE_KERNEL_INTERPRETER_ID
from .nodes import (
    BinaryExpr,
    Item,
    Kernel,
    NodeId,
    binding_ref,
    channel,
    dependency,
    for_stmt,
    item_ref,
    kernel,
    let,
    literal,
    param,
    process,
    process_graph,
    process_step,
    receive_expr,
    ref,
    region,
    send_stmt,
    task,
    task_graph,
    to_payload,
)
from .semantics import KernelArg, KernelIR, WorkloadIR, WorkloadTask


def program_module_from_items(
    *items: Item,
    entry: str,
    interpreter_id: str,
    kernel_ir: KernelIR,
    workload_ir: WorkloadIR,
    analyses: dict[str, dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
) -> ProgramModule:
    if not items:
        raise ValueError("program_module_from_items requires at least one Item")
    return ProgramModule(
        items=ProgramItems(
            canonical_ast={
                "schema": "htp.program_ast.v1",
                "program": {
                    "entry": entry,
                    "typed_items": [to_payload(item) for item in items],
                },
            },
            kernel_ir=kernel_ir,
            workload_ir=workload_ir,
            typed_items=tuple(items),
        ),
        aspects=ProgramAspects(
            types=TypesAspect(schema="htp.types.v1"),
            layout=LayoutAspect(schema="htp.layout.v1"),
            effects=EffectsAspect(schema="htp.effects.v1"),
            schedule=ScheduleAspect(schema="htp.schedule.v1"),
        ),
        analyses=dict(analyses or {}),
        identity=ProgramIdentity(
            entities={"schema": "htp.ids.entities.v1", "entities": [], "node_to_entity": []},
            bindings={"schema": "htp.ids.bindings.v1", "scopes": [], "bindings": [], "name_uses": []},
        ),
        entrypoints=(ProgramEntrypoint(name=entry, interpreter_id=interpreter_id),),
        meta={
            **dialect_activation_payload("htp.core"),
            **dict(meta or {}),
        },
    )


def program_module_from_kernels(
    *kernels: Kernel,
    entry: str = "run",
    interpreter_id: str = NODE_KERNEL_INTERPRETER_ID,
    analyses: dict[str, dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
) -> ProgramModule:
    if not kernels:
        raise ValueError("program_module_from_kernels requires at least one Kernel")
    primary = kernels[0]
    return program_module_from_items(
        *kernels,
        entry=entry,
        interpreter_id=interpreter_id,
        kernel_ir=KernelIR(
            entry=primary.name,
            args=tuple(
                KernelArg(
                    name=parameter.name,
                    kind=parameter.kind,
                    dtype=parameter.dtype,
                )
                for parameter in primary.params
            ),
            buffers=(),
            ops=(),
        ),
        workload_ir=WorkloadIR(
            entry=entry,
            tasks=(
                WorkloadTask(
                    task_id="task0",
                    kind="kernel_call",
                    kernel=primary.name,
                    args=tuple(parameter.name for parameter in primary.params),
                    entity_id=f"{primary.item_id.value}:task0",
                ),
            ),
            channels=(),
            dependencies=(),
        ),
        analyses=analyses,
        meta=meta,
    )


def build_tile_streamed_gemm_core_module() -> ProgramModule:
    kernel_item = kernel(
        "item.tile_streamed_gemm",
        "tile_streamed_gemm",
        params=(
            param("param.a", "sym.a", "a", kind="buffer", dtype="f32"),
            param("param.b", "sym.b", "b", kind="buffer", dtype="f32"),
            param("param.out", "sym.out", "out", kind="buffer", dtype="f32"),
            param("param.m", "sym.m", "m", kind="shape", dtype="i32"),
            param("param.n", "sym.n", "n", kind="shape", dtype="i32"),
            param("param.k", "sym.k", "k", kind="shape", dtype="i32"),
        ),
        body=region(
            "region.kernel.tile_streamed_gemm",
            for_stmt(
                "stmt.for.tile_k",
                "binding.tile_k",
                "tile_k",
                start=literal("expr.tile_k.start", 0),
                stop=ref("expr.tile_k.stop", "sym.k", "k"),
                step=literal("expr.tile_k.step", 16),
                body=region(
                    "region.kernel.tile_loop",
                    let(
                        "stmt.accum.partial",
                        "sym.partial",
                        "partial",
                        BinaryExpr(
                            node_id=NodeId("expr.partial.matmul"),
                            op="add",
                            lhs=ref("expr.partial.a", "sym.a", "a"),
                            rhs=ref("expr.partial.b", "sym.b", "b"),
                        ),
                    ),
                ),
            ),
            let(
                "stmt.out.final",
                "sym.final",
                "final_tile",
                ref("expr.final.partial", "sym.partial", "partial"),
            ),
        ),
    )
    kernel_handle = item_ref("itemref.tile_streamed_gemm", "item.tile_streamed_gemm", "tile_streamed_gemm")
    task_item = task_graph(
        "item.tile_schedule",
        "tile_schedule",
        tasks=(
            task(
                "task.load_tiles",
                "load_tiles",
                kernel=kernel_handle,
                args=(ref("taskarg.load.a", "sym.a", "a"), ref("taskarg.load.b", "sym.b", "b")),
                attrs={"role": "producer"},
            ),
            task(
                "task.mma_tiles",
                "mma_tiles",
                kernel=kernel_handle,
                args=(ref("taskarg.mma.a", "sym.a", "a"), ref("taskarg.mma.b", "sym.b", "b")),
                attrs={"role": "consumer"},
            ),
        ),
        dependencies=(dependency("dep.load_to_mma", src_task="load_tiles", dst_task="mma_tiles"),),
        body=region(
            "region.task_graph.tile_schedule",
            let(
                "stmt.task_graph.tile_index",
                "sym.current_tile",
                "current_tile",
                binding_ref("expr.task_graph.tile_k", "binding.tile_k", "tile_k"),
            ),
        ),
    )
    tile_stream = channel(
        "item.channel.tile_stream",
        "tile_stream",
        channel_id="chan.tile_stream",
        dtype="f32",
        capacity=2,
    )
    process_item = process_graph(
        "item.tile_pipeline",
        "tile_pipeline",
        channels=(tile_stream,),
        processes=(
            process(
                "process.dispatch",
                "dispatch",
                kernel=kernel_handle,
                args=(ref("processarg.dispatch.a", "sym.a", "a"),),
                steps=(
                    process_step(
                        "process.step.dispatch.put",
                        kind="put",
                        channel_id="chan.tile_stream",
                        attrs={"tile": "a_tile"},
                    ),
                ),
                attrs={"role": "producer"},
            ),
        ),
        body=region(
            "region.process_graph.tile_pipeline",
            let(
                "stmt.process_graph.recv",
                "sym.recv_tile",
                "recv_tile",
                receive_expr("expr.process_graph.recv", channel_id="chan.tile_stream"),
            ),
            send_stmt(
                "stmt.process_graph.send",
                channel_id="chan.tile_stream",
                value=ref("expr.process_graph.send_value", "sym.recv_tile", "recv_tile"),
            ),
        ),
    )
    return program_module_from_items(
        kernel_item,
        task_item,
        process_item,
        entry="run",
        interpreter_id=NODE_KERNEL_INTERPRETER_ID,
        kernel_ir=KernelIR(
            entry=kernel_item.name,
            args=tuple(
                KernelArg(name=parameter.name, kind=parameter.kind, dtype=parameter.dtype)
                for parameter in kernel_item.params
            ),
            buffers=(),
            ops=(),
        ),
        workload_ir=WorkloadIR(
            entry="run",
            tasks=(
                WorkloadTask(
                    task_id="load_tiles",
                    kind="kernel_call",
                    kernel=kernel_item.name,
                    args=("a", "b"),
                    entity_id="tile_schedule:load_tiles",
                ),
                WorkloadTask(
                    task_id="dispatch",
                    kind="process",
                    kernel=kernel_item.name,
                    args=("a",),
                    entity_id="tile_pipeline:dispatch",
                ),
            ),
            channels=({"name": "tile_stream", "dtype": "f32", "capacity": 2, "protocol": "fifo"},),
            dependencies=({"src": "load_tiles", "dst": "mma_tiles"},),
            processes=(
                {
                    "name": "dispatch",
                    "task_id": "dispatch",
                    "kernel": kernel_item.name,
                    "steps": [{"kind": "put", "channel": "tile_stream"}],
                },
            ),
        ),
        meta={"variant": "core"},
    )


__all__ = [
    "build_tile_streamed_gemm_core_module",
    "program_module_from_items",
    "program_module_from_kernels",
]
