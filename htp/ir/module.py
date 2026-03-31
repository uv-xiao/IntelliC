from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
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
from .interpreter import SNAPSHOT_INTERPRETER_ID, run_program_module
from .semantics import (
    KernelIR,
    WorkloadIR,
    kernel_ir_from_payload,
    kernel_ir_payload,
    workload_ir_from_payload,
    workload_ir_payload,
)

if TYPE_CHECKING:
    from .nodes import Node

PROGRAM_MODULE_SCHEMA_ID = "htp.program_module.v1"


@dataclass(frozen=True)
class ProgramItems:
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
    name: str
    kind: str = "stage_run"
    interpreter_id: str = SNAPSHOT_INTERPRETER_ID


@dataclass(frozen=True)
class ProgramModule:
    items: ProgramItems
    aspects: ProgramAspects
    analyses: dict[str, AnalysisRecord | Mapping[str, Any]] = field(default_factory=dict)
    identity: ProgramIdentity = field(default_factory=lambda: ProgramIdentity(entities={}, bindings={}))
    entrypoints: tuple[ProgramEntrypoint, ...] = (ProgramEntrypoint("run"),)
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.analyses and not all(isinstance(value, AnalysisRecord) for value in self.analyses.values()):
            object.__setattr__(
                self,
                "analyses",
                {
                    str(key): (
                        value if isinstance(value, AnalysisRecord) else analysis_record_from_payload(value)
                    )
                    for key, value in self.analyses.items()
                    if isinstance(value, Mapping) or isinstance(value, AnalysisRecord)
                },
            )

    def to_payload(self) -> dict[str, Any]:
        from .nodes import to_payload

        items_payload = {
            "canonical_ast": dict(self.items.canonical_ast),
            "kernel_ir": kernel_ir_payload(self.items.kernel_ir),
            "workload_ir": workload_ir_payload(self.items.workload_ir),
        }
        if self.items.typed_items:
            items_payload["typed_items"] = [to_payload(item) for item in self.items.typed_items]
        return {
            "schema": PROGRAM_MODULE_SCHEMA_ID,
            "items": items_payload,
            "aspects": {
                "types": self.aspects.types.to_payload(),
                "layout": self.aspects.layout.to_payload(),
                "effects": self.aspects.effects.to_payload(),
                "schedule": self.aspects.schedule.to_payload(),
            },
            "analyses": {key: value.to_payload() for key, value in self.analyses.items()},
            "identity": {
                "entities": self.identity.entities.to_payload(),
                "bindings": self.identity.bindings.to_payload(),
                "entity_map": (
                    None if self.identity.entity_map is None else self.identity.entity_map.to_payload()
                ),
                "binding_map": (
                    None if self.identity.binding_map is None else self.identity.binding_map.to_payload()
                ),
            },
            "entrypoints": [asdict(item) for item in self.entrypoints],
            "meta": dict(self.meta),
        }

    def run(
        self,
        *args: Any,
        entry: str | None = None,
        mode: str = "sim",
        runtime: Any | None = None,
        trace: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        entry_spec = self.entrypoint(entry)
        return run_program_module(
            self,
            interpreter_id=entry_spec.interpreter_id,
            entry=entry_spec.name,
            args=args,
            kwargs=kwargs,
            mode=mode,
            runtime=runtime,
            trace=trace,
        )

    def entrypoint(self, name: str | None = None) -> ProgramEntrypoint:
        if name is None:
            return self.entrypoints[0]
        for item in self.entrypoints:
            if item.name == name:
                return item
        raise KeyError(f"Unknown ProgramModule entrypoint: {name}")

    def to_program_dict(self) -> dict[str, Any]:
        program = self.to_state_dict()
        canonical_ast = dict(program.pop("canonical_ast", {}))
        program.update(canonical_ast)
        return program

    def to_state_dict(self) -> dict[str, Any]:
        program = dict(self.meta.get("program_extras", {}))
        if "entry" not in program:
            entry = self.items.canonical_ast.get("entry")
            if entry is None and isinstance(self.items.canonical_ast.get("program"), Mapping):
                entry = self.items.canonical_ast["program"].get("entry")
            if entry is None:
                entry = self.items.workload_ir.entry or self.items.kernel_ir.entry
            if entry is None:
                entry = self.entrypoints[0].name
            program["entry"] = str(entry)
        program["canonical_ast"] = dict(self.items.canonical_ast)
        program["kernel_ir"] = kernel_ir_payload(self.items.kernel_ir)
        program["workload_ir"] = workload_ir_payload(self.items.workload_ir)
        if self.items.typed_items:
            from .nodes import to_payload

            program["typed_items_payload"] = [to_payload(item) for item in self.items.typed_items]
        program["types"] = self.aspects.types.to_payload()
        program["layout"] = self.aspects.layout.to_payload()
        program["effects"] = self.aspects.effects.to_payload()
        program["schedule"] = self.aspects.schedule.to_payload()
        program["analysis"] = {key: value.to_payload() for key, value in self.analyses.items()}
        program["entities_payload"] = self.identity.entities.to_payload()
        program["bindings_payload"] = self.identity.bindings.to_payload()
        if self.identity.entity_map is not None:
            program["entity_map_payload"] = self.identity.entity_map.to_payload()
        if self.identity.binding_map is not None:
            program["binding_map_payload"] = self.identity.binding_map.to_payload()
        program["program_module"] = self.to_payload()
        program["entrypoints"] = [asdict(item) for item in self.entrypoints]
        if self.meta:
            public_meta = {key: value for key, value in self.meta.items() if key != "program_extras"}
            if public_meta:
                program["meta"] = public_meta
        return program

    @classmethod
    def from_program_dict(
        cls,
        program: Mapping[str, Any],
        *,
        analyses: Mapping[str, Mapping[str, Any]] | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> ProgramModule:
        from .nodes import from_payload

        analysis_payload = dict(analyses or program.get("analysis", {}))
        entry = str(program.get("entry", "run"))
        known_keys = {
            "analysis",
            "bindings_payload",
            "canonical_ast",
            "effects",
            "entities_payload",
            "entry",
            "entrypoints",
            "entity_map_payload",
            "kernel_ir",
            "layout",
            "meta",
            "program_module",
            "schedule",
            "types",
            "typed_items_payload",
            "workload_ir",
            "binding_map_payload",
        }
        extras = {str(key): value for key, value in program.items() if key not in known_keys}
        meta_payload = dict(meta or program.get("meta", {}))
        if extras:
            meta_payload["program_extras"] = extras
        return cls(
            items=ProgramItems(
                canonical_ast=dict(
                    program.get("canonical_ast", {"schema": "htp.program_ast.v1", "program": dict(program)})
                ),
                kernel_ir=dict(program.get("kernel_ir", {})),
                workload_ir=dict(program.get("workload_ir", {})),
                typed_items=tuple(
                    from_payload(dict(item))
                    for item in program.get("typed_items_payload", ())
                    if isinstance(item, Mapping)
                ),
            ),
            aspects=ProgramAspects(
                types=dict(program.get("types", {})),
                layout=dict(program.get("layout", {})),
                effects=dict(program.get("effects", {})),
                schedule=dict(program.get("schedule", {})),
            ),
            analyses={key: analysis_record_from_payload(value) for key, value in analysis_payload.items()},
            identity=ProgramIdentity(
                entities=dict(program.get("entities_payload", {})),
                bindings=dict(program.get("bindings_payload", {})),
                entity_map=(
                    dict(program["entity_map_payload"])
                    if isinstance(program.get("entity_map_payload"), Mapping)
                    else None
                ),
                binding_map=(
                    dict(program["binding_map_payload"])
                    if isinstance(program.get("binding_map_payload"), Mapping)
                    else None
                ),
            ),
            entrypoints=tuple(
                ProgramEntrypoint(
                    str(item.get("name", entry)),
                    str(item.get("kind", "stage_run")),
                    str(item.get("interpreter_id", SNAPSHOT_INTERPRETER_ID)),
                )
                for item in program.get("entrypoints", ())
                if isinstance(item, Mapping)
            )
            or (ProgramEntrypoint("run"),),
            meta=meta_payload,
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ProgramModule:
        from .nodes import from_payload

        items_payload = dict(payload.get("items", {}))
        aspects_payload = dict(payload.get("aspects", {}))
        identity_payload = dict(payload.get("identity", {}))
        analyses_payload = {
            str(key): dict(value)
            for key, value in dict(payload.get("analyses", {})).items()
            if isinstance(value, Mapping)
        }
        entrypoints_payload = tuple(
            ProgramEntrypoint(
                str(item.get("name", "run")),
                str(item.get("kind", "stage_run")),
                str(item.get("interpreter_id", SNAPSHOT_INTERPRETER_ID)),
            )
            for item in payload.get("entrypoints", ())
            if isinstance(item, Mapping)
        ) or (ProgramEntrypoint("run"),)
        return cls(
            items=ProgramItems(
                canonical_ast=dict(items_payload.get("canonical_ast", {})),
                kernel_ir=dict(items_payload.get("kernel_ir", {})),
                workload_ir=dict(items_payload.get("workload_ir", {})),
                typed_items=tuple(
                    from_payload(dict(item))
                    for item in items_payload.get("typed_items", ())
                    if isinstance(item, Mapping)
                ),
            ),
            aspects=ProgramAspects(
                types=dict(aspects_payload.get("types", {})),
                layout=dict(aspects_payload.get("layout", {})),
                effects=dict(aspects_payload.get("effects", {})),
                schedule=dict(aspects_payload.get("schedule", {})),
            ),
            analyses=analyses_payload,
            identity=ProgramIdentity(
                entities=dict(identity_payload.get("entities", {})),
                bindings=dict(identity_payload.get("bindings", {})),
                entity_map=(
                    dict(identity_payload["entity_map"])
                    if isinstance(identity_payload.get("entity_map"), Mapping)
                    else None
                ),
                binding_map=(
                    dict(identity_payload["binding_map"])
                    if isinstance(identity_payload.get("binding_map"), Mapping)
                    else None
                ),
            ),
            entrypoints=entrypoints_payload,
            meta=dict(payload.get("meta", {})),
        )


def ensure_program_module(program: ProgramModule | Mapping[str, Any]) -> ProgramModule:
    if isinstance(program, ProgramModule):
        return program
    return ProgramModule.from_program_dict(program)


def program_dict_view(program: ProgramModule | Mapping[str, Any]) -> dict[str, Any]:
    return ensure_program_module(program).to_state_dict()


__all__ = [
    "PROGRAM_MODULE_SCHEMA_ID",
    "ProgramAspects",
    "ProgramEntrypoint",
    "ProgramIdentity",
    "ProgramItems",
    "ProgramModule",
    "ensure_program_module",
    "program_dict_view",
]
