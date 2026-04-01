"""Shared frontend helpers for lowering public authoring surfaces to ProgramModule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..core.aspects import EffectsAspect, LayoutAspect, ScheduleAspect, TypesAspect
from ..core.semantics import (
    WorkloadChannel,
    WorkloadDependency,
    WorkloadIR,
    WorkloadProcess,
    WorkloadTask,
)
from ..dialects.registry import dialect_activation_payload
from ..program.module import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems, ProgramModule

if TYPE_CHECKING:
    from ..core.nodes import Node


@dataclass(frozen=True)
class FrontendWorkload:
    entry: str
    tasks: tuple[WorkloadTask, ...]
    channels: tuple[WorkloadChannel, ...] = ()
    dependencies: tuple[WorkloadDependency, ...] = ()
    processes: tuple[WorkloadProcess, ...] = ()
    routine: dict[str, Any] | None = None

    def to_workload_ir(self) -> WorkloadIR:
        return WorkloadIR(
            entry=self.entry,
            tasks=self.tasks,
            channels=self.channels,
            dependencies=self.dependencies,
            processes=self.processes,
            routine=None if self.routine is None else dict(self.routine),
        )


def build_frontend_program_module(
    *,
    kernel_module: ProgramModule,
    authored_program: dict[str, Any],
    workload: FrontendWorkload,
    source_surface: str,
    active_dialects: tuple[str, ...],
    typed_items: tuple[Node, ...] = (),
) -> ProgramModule:
    return ProgramModule(
        items=ProgramItems(
            canonical_ast={"schema": "htp.program_ast.v1", "program": authored_program},
            kernel_ir=kernel_module.items.kernel_ir,
            workload_ir=workload.to_workload_ir(),
            typed_items=kernel_module.items.typed_items + tuple(typed_items),
        ),
        aspects=ProgramAspects(
            types=TypesAspect(schema="htp.types.v1"),
            layout=LayoutAspect(schema="htp.layout.v1"),
            effects=EffectsAspect(schema="htp.effects.v1"),
            schedule=ScheduleAspect(schema="htp.schedule.v1"),
        ),
        analyses=kernel_module.analyses,
        identity=ProgramIdentity(
            entities=kernel_module.identity.entities,
            bindings=kernel_module.identity.bindings,
            entity_map=kernel_module.identity.entity_map,
            binding_map=kernel_module.identity.binding_map,
        ),
        entrypoints=(ProgramEntrypoint("run"),),
        meta={
            "source_surface": source_surface,
            **dialect_activation_payload(*active_dialects),
            "program_extras": authored_program,
        },
    )


def kernel_spec_from_payload(payload: dict[str, Any]):
    """Rebuild a public ``KernelSpec`` from a legacy/kernel payload mapping."""

    from htp.kernel import KernelArgSpec, KernelSpec

    return KernelSpec(
        name=str(payload["name"]),
        args=tuple(
            KernelArgSpec(
                name=str(item["name"]) if item.get("name") is not None else None,
                kind=str(item["kind"]),
                dtype=str(item["dtype"]),
                shape=tuple(str(dim) for dim in item.get("shape", ())),
                role=str(item["role"]) if item.get("role") is not None else None,
                memory_space=(str(item["memory_space"]) if item.get("memory_space") is not None else None),
                axis_layout=tuple(str(dim) for dim in item.get("axis_layout", ())),
                distribution=tuple(dict(dist) for dist in item.get("distribution", ())),
                attrs=dict(item.get("attrs", {})) or None,
            )
            for item in payload.get("args", ())
        ),
        ops=tuple(dict(item) for item in payload.get("ops", ())),
    )


__all__ = ["FrontendWorkload", "build_frontend_program_module", "kernel_spec_from_payload"]
