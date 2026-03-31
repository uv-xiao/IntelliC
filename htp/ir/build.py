from __future__ import annotations

from typing import Any

from .aspects import EffectsAspect, LayoutAspect, ScheduleAspect, TypesAspect
from .dialects import dialect_activation_payload
from .module import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems, ProgramModule
from .node_exec import NODE_KERNEL_INTERPRETER_ID
from .nodes import Kernel, to_payload
from .semantics import KernelArg, KernelIR, WorkloadIR, WorkloadTask


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
    return ProgramModule(
        items=ProgramItems(
            canonical_ast={
                "schema": "htp.program_ast.v1",
                "program": {
                    "entry": entry,
                    "typed_items": [to_payload(kernel) for kernel in kernels],
                },
            },
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
            typed_items=tuple(kernels),
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


__all__ = ["program_module_from_kernels"]
