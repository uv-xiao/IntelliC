"""ProgramModule composition helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..core.semantics import WorkloadIR
from ..dialects.registry import dialect_activation_payload
from ..interpreters.entrypoints import NODE_PROGRAM_INTERPRETER_ID
from .components import ProgramEntrypoint, ProgramItems
from .module import ProgramModule


def compose_program_modules(
    *modules: ProgramModule,
    canonical_program: Mapping[str, Any],
    source_surface: str,
    entry: str = "run",
    routine: Mapping[str, Any] | None = None,
    interpreter_id: str = NODE_PROGRAM_INTERPRETER_ID,
    meta: Mapping[str, Any] | None = None,
) -> ProgramModule:
    if not modules:
        raise ValueError("compose_program_modules requires at least one ProgramModule")
    primary = modules[0]
    _ensure_compatible_modules(modules)
    active_dialects = _ordered_active_dialects(modules)
    workload_ir = WorkloadIR(
        entry=entry,
        tasks=tuple(task for module in modules for task in module.items.workload_ir.tasks),
        channels=tuple(channel for module in modules for channel in module.items.workload_ir.channels),
        dependencies=tuple(
            dependency for module in modules for dependency in module.items.workload_ir.dependencies
        ),
        processes=tuple(process for module in modules for process in module.items.workload_ir.processes),
        routine=None if routine is None else dict(routine),
    )
    merged_meta = {
        "source_surface": source_surface,
        **dialect_activation_payload(*active_dialects),
        "program_extras": dict(canonical_program),
        **dict(meta or {}),
    }
    return ProgramModule(
        items=ProgramItems(
            canonical_ast={"schema": "htp.program_ast.v1", "program": dict(canonical_program)},
            kernel_ir=primary.items.kernel_ir,
            workload_ir=workload_ir,
            typed_items=tuple(item for module in modules for item in module.items.typed_items),
        ),
        aspects=primary.aspects,
        analyses=_merged_analyses(modules),
        identity=primary.identity,
        entrypoints=(ProgramEntrypoint(name=entry, interpreter_id=interpreter_id),),
        meta=merged_meta,
    )


def _ensure_compatible_modules(modules: Sequence[ProgramModule]) -> None:
    primary = modules[0]
    for module in modules[1:]:
        if module.items.kernel_ir != primary.items.kernel_ir:
            raise ValueError("compose_program_modules requires identical kernel_ir across modules")
        if module.aspects != primary.aspects:
            raise ValueError("compose_program_modules requires identical aspects across modules")
        if module.identity != primary.identity:
            raise ValueError("compose_program_modules requires identical identity across modules")


def _ordered_active_dialects(modules: Sequence[ProgramModule]) -> tuple[str, ...]:
    active: list[str] = []
    for module in modules:
        for dialect_id in module.meta.get("active_dialects", ()):
            if dialect_id not in active:
                active.append(str(dialect_id))
    return tuple(active)


def _merged_analyses(modules: Sequence[ProgramModule]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for module in modules:
        merged.update(module.analyses)
    return merged


__all__ = ["compose_program_modules"]
