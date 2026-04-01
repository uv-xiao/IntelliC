"""Typed ``ProgramModule`` component objects separated from serialization logic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .analysis_state import AnalysisRecord, analysis_record_from_payload
from .aspects import (
    EffectsAspect,
    LayoutAspect,
    ScheduleAspect,
    TypesAspect,
    effects_aspect_from_payload,
    layout_aspect_from_payload,
    schedule_aspect_from_payload,
    types_aspect_from_payload,
)
from .identity_state import (
    BindingTable,
    EntityTable,
    RewriteMap,
    bindings_from_payload,
    entities_from_payload,
    rewrite_map_from_payload,
)
from .interpreter import SNAPSHOT_INTERPRETER_ID
from .semantics import KernelIR, WorkloadIR, kernel_ir_from_payload, workload_ir_from_payload

if TYPE_CHECKING:
    from .nodes import Node


@dataclass(frozen=True)
class ProgramItems:
    """Typed top-level program payload owned by ``ProgramModule``."""

    canonical_ast: dict[str, Any]
    kernel_ir: KernelIR | dict[str, Any]
    workload_ir: WorkloadIR | dict[str, Any]
    typed_items: tuple[Node, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.kernel_ir, Mapping):
            object.__setattr__(self, "kernel_ir", kernel_ir_from_payload(dict(self.kernel_ir)))
        if isinstance(self.workload_ir, Mapping):
            object.__setattr__(self, "workload_ir", workload_ir_from_payload(dict(self.workload_ir)))
        if self.typed_items and isinstance(self.typed_items[0], Mapping):
            from .nodes import from_payload

            object.__setattr__(
                self,
                "typed_items",
                tuple(from_payload(dict(item)) for item in self.typed_items if isinstance(item, Mapping)),
            )


@dataclass(frozen=True)
class ProgramAspects:
    """Typed long-lived semantic attachments for a ``ProgramModule``."""

    types: TypesAspect | Mapping[str, Any]
    layout: LayoutAspect | Mapping[str, Any]
    effects: EffectsAspect | Mapping[str, Any]
    schedule: ScheduleAspect | Mapping[str, Any]

    def __post_init__(self) -> None:
        if isinstance(self.types, Mapping) and not isinstance(self.types, TypesAspect):
            object.__setattr__(self, "types", types_aspect_from_payload(self.types))
        if isinstance(self.layout, Mapping) and not isinstance(self.layout, LayoutAspect):
            object.__setattr__(self, "layout", layout_aspect_from_payload(self.layout))
        if isinstance(self.effects, Mapping) and not isinstance(self.effects, EffectsAspect):
            object.__setattr__(self, "effects", effects_aspect_from_payload(self.effects))
        if isinstance(self.schedule, Mapping) and not isinstance(self.schedule, ScheduleAspect):
            object.__setattr__(self, "schedule", schedule_aspect_from_payload(self.schedule))


@dataclass(frozen=True)
class ProgramIdentity:
    """Typed identity/provenance state for a ``ProgramModule``."""

    entities: EntityTable | Mapping[str, Any]
    bindings: BindingTable | Mapping[str, Any]
    entity_map: RewriteMap | Mapping[str, Any] | None = None
    binding_map: RewriteMap | Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.entities, Mapping) and not isinstance(self.entities, EntityTable):
            object.__setattr__(self, "entities", entities_from_payload(self.entities))
        if isinstance(self.bindings, Mapping) and not isinstance(self.bindings, BindingTable):
            object.__setattr__(self, "bindings", bindings_from_payload(self.bindings))
        if isinstance(self.entity_map, Mapping) and not isinstance(self.entity_map, RewriteMap):
            object.__setattr__(
                self,
                "entity_map",
                rewrite_map_from_payload(self.entity_map, default_schema="htp.entity_map.v1"),
            )
        if isinstance(self.binding_map, Mapping) and not isinstance(self.binding_map, RewriteMap):
            object.__setattr__(
                self,
                "binding_map",
                rewrite_map_from_payload(self.binding_map, default_schema="htp.binding_map.v1"),
            )


@dataclass(frozen=True)
class ProgramEntrypoint:
    """Named execution entry exposed by a ``ProgramModule``."""

    name: str
    kind: str = "stage_run"
    interpreter_id: str = SNAPSHOT_INTERPRETER_ID


def normalize_analyses(
    analyses: dict[str, AnalysisRecord | Mapping[str, Any]],
) -> dict[str, AnalysisRecord]:
    """Convert mixed mapping/record analysis state into typed records."""

    if not analyses:
        return {}
    if all(isinstance(value, AnalysisRecord) for value in analyses.values()):
        return {str(key): value for key, value in analyses.items() if isinstance(value, AnalysisRecord)}
    return {
        str(key): value if isinstance(value, AnalysisRecord) else analysis_record_from_payload(value)
        for key, value in analyses.items()
        if isinstance(value, Mapping) or isinstance(value, AnalysisRecord)
    }


__all__ = [
    "ProgramAspects",
    "ProgramEntrypoint",
    "ProgramIdentity",
    "ProgramItems",
    "normalize_analyses",
]
