"""Kernel-surface lowering into typed ``ProgramModule`` objects."""

from __future__ import annotations

from typing import Any

from htp.ir.aspects import EffectsAspect, LayoutAspect, ScheduleAspect, TypesAspect
from htp.ir.dialects import dialect_activation_payload
from htp.ir.module import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems, ProgramModule
from htp.ir.semantics import KernelArg, KernelIR, KernelOp, WorkloadIR, WorkloadTask
from htp.kernel import KernelArgSpec, KernelSpec


def build_kernel_program_module(spec: KernelSpec) -> ProgramModule:
    """Lower a public ``KernelSpec`` into a typed ``ProgramModule``."""

    authored_program = spec.to_program()
    runtime_args = tuple(argument for argument in spec.args if argument.name is not None)
    kernel_ir = KernelIR(
        entry=spec.name,
        args=tuple(_semantic_kernel_arg(argument) for argument in runtime_args),
        buffers=tuple(
            _semantic_kernel_arg(argument) for argument in runtime_args if argument.kind == "buffer"
        ),
        ops=tuple(_semantic_kernel_op(spec.name, index=index, op=op) for index, op in enumerate(spec.ops)),
    )
    workload_ir = WorkloadIR(
        entry=spec.name,
        tasks=(
            WorkloadTask(
                task_id="task0",
                kind="kernel_call",
                kernel=spec.name,
                args=tuple(argument.name for argument in runtime_args if argument.name is not None),
                entity_id=f"{spec.name}:task0",
            ),
        ),
        channels=(),
        dependencies=(),
    )
    return ProgramModule(
        items=ProgramItems(
            canonical_ast={"schema": "htp.program_ast.v1", "program": authored_program},
            kernel_ir=kernel_ir,
            workload_ir=workload_ir,
        ),
        aspects=ProgramAspects(
            types=TypesAspect(schema="htp.types.v1"),
            layout=LayoutAspect(schema="htp.layout.v1"),
            effects=EffectsAspect(schema="htp.effects.v1"),
            schedule=ScheduleAspect(schema="htp.schedule.v1"),
        ),
        identity=ProgramIdentity(
            entities={"schema": "htp.ids.entities.v1", "entities": [], "node_to_entity": []},
            bindings={"schema": "htp.ids.bindings.v1", "scopes": [], "bindings": [], "name_uses": []},
        ),
        entrypoints=(ProgramEntrypoint("run"),),
        meta={
            "source_surface": "htp.kernel.KernelSpec",
            **dialect_activation_payload("htp.core", "htp.kernel"),
            "program_extras": authored_program,
        },
    )


def _semantic_kernel_arg(argument: KernelArgSpec) -> KernelArg:
    if argument.name is None:
        raise ValueError("Kernel arguments must have names before ProgramModule lowering")
    return KernelArg(
        name=argument.name,
        kind=argument.kind,
        dtype=argument.dtype,
        shape=argument.shape,
        memory_space=argument.memory_space,
        role=argument.role,
        distribution=argument.distribution,
    )


def _semantic_kernel_op(entry: str, *, index: int, op: dict[str, Any]) -> KernelOp:
    read_keys = ("lhs", "rhs", "src", "source", "input", "x", "y", "token", "channel")
    write_keys = ("out", "dst", "target", "output")
    reads = tuple(str(op[key]) for key in read_keys if op.get(key) is not None)
    writes = tuple(str(op[key]) for key in write_keys if op.get(key) is not None)
    attrs = {str(key): value for key, value in op.items() if key not in {"op", *read_keys, *write_keys}}
    return KernelOp(
        op_id=f"op{index}",
        entity_id=f"{entry}:E{index}",
        op=str(op.get("op", "unknown")),
        intrinsic=str(op.get("intrinsic", op.get("op", "unknown"))),
        inputs=reads,
        outputs=writes,
        attrs=attrs,
        effects={"reads": reads, "writes": writes},
    )


__all__ = ["build_kernel_program_module"]
