"""ProgramModule payload/state serialization helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from .analysis_state import analysis_record_from_payload
from .interpreter import SNAPSHOT_INTERPRETER_ID
from .program_components import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems
from .semantics import kernel_ir_payload, workload_ir_payload

if TYPE_CHECKING:
    from .module import ProgramModule


PROGRAM_MODULE_SCHEMA_ID = "htp.program_module.v1"


def program_module_to_payload(module: ProgramModule) -> dict[str, Any]:
    from .nodes import to_payload

    items_payload = {
        "canonical_ast": dict(module.items.canonical_ast),
        "kernel_ir": kernel_ir_payload(module.items.kernel_ir),
        "workload_ir": workload_ir_payload(module.items.workload_ir),
    }
    if module.items.typed_items:
        items_payload["typed_items"] = [to_payload(item) for item in module.items.typed_items]
    return {
        "schema": PROGRAM_MODULE_SCHEMA_ID,
        "items": items_payload,
        "aspects": {
            "types": module.aspects.types.to_payload(),
            "layout": module.aspects.layout.to_payload(),
            "effects": module.aspects.effects.to_payload(),
            "schedule": module.aspects.schedule.to_payload(),
        },
        "analyses": {key: value.to_payload() for key, value in module.analyses.items()},
        "identity": {
            "entities": module.identity.entities.to_payload(),
            "bindings": module.identity.bindings.to_payload(),
            "entity_map": None
            if module.identity.entity_map is None
            else module.identity.entity_map.to_payload(),
            "binding_map": None
            if module.identity.binding_map is None
            else module.identity.binding_map.to_payload(),
        },
        "entrypoints": [asdict(item) for item in module.entrypoints],
        "meta": dict(module.meta),
    }


def program_module_to_state_dict(module: ProgramModule) -> dict[str, Any]:
    from .nodes import to_payload

    program = dict(module.meta.get("program_extras", {}))
    if "entry" not in program:
        entry = module.items.canonical_ast.get("entry")
        if entry is None and isinstance(module.items.canonical_ast.get("program"), Mapping):
            entry = module.items.canonical_ast["program"].get("entry")
        if entry is None:
            entry = module.items.workload_ir.entry or module.items.kernel_ir.entry
        if entry is None:
            entry = module.entrypoints[0].name
        program["entry"] = str(entry)
    program["canonical_ast"] = dict(module.items.canonical_ast)
    program["kernel_ir"] = kernel_ir_payload(module.items.kernel_ir)
    program["workload_ir"] = workload_ir_payload(module.items.workload_ir)
    if module.items.typed_items:
        program["typed_items_payload"] = [to_payload(item) for item in module.items.typed_items]
    program["types"] = module.aspects.types.to_payload()
    program["layout"] = module.aspects.layout.to_payload()
    program["effects"] = module.aspects.effects.to_payload()
    program["schedule"] = module.aspects.schedule.to_payload()
    program["analysis"] = {key: value.to_payload() for key, value in module.analyses.items()}
    program["entities_payload"] = module.identity.entities.to_payload()
    program["bindings_payload"] = module.identity.bindings.to_payload()
    if module.identity.entity_map is not None:
        program["entity_map_payload"] = module.identity.entity_map.to_payload()
    if module.identity.binding_map is not None:
        program["binding_map_payload"] = module.identity.binding_map.to_payload()
    program["program_module"] = program_module_to_payload(module)
    program["entrypoints"] = [asdict(item) for item in module.entrypoints]
    if module.meta:
        public_meta = {key: value for key, value in module.meta.items() if key != "program_extras"}
        if public_meta:
            program["meta"] = public_meta
    return program


def program_module_to_program_dict(module: ProgramModule) -> dict[str, Any]:
    program = program_module_to_state_dict(module)
    canonical_ast = dict(program.pop("canonical_ast", {}))
    program.update(canonical_ast)
    return program


def program_module_from_program_dict(
    program: Mapping[str, Any],
    *,
    analyses: Mapping[str, Mapping[str, Any]] | None = None,
    meta: Mapping[str, Any] | None = None,
) -> ProgramModule:
    from .module import ProgramModule
    from .nodes import from_payload

    analysis_payload = dict(analyses or program.get("analysis", {}))
    entry = str(program.get("entry", "run"))
    known_keys = {
        "analysis",
        "bindings_payload",
        "binding_map_payload",
        "canonical_ast",
        "effects",
        "entities_payload",
        "entity_map_payload",
        "entry",
        "entrypoints",
        "kernel_ir",
        "layout",
        "meta",
        "program_module",
        "schedule",
        "types",
        "typed_items_payload",
        "workload_ir",
    }
    extras = {str(key): value for key, value in program.items() if key not in known_keys}
    meta_payload = dict(meta or program.get("meta", {}))
    if extras:
        meta_payload["program_extras"] = extras
    return ProgramModule(
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


def program_module_from_payload(payload: Mapping[str, Any]) -> ProgramModule:
    from .module import ProgramModule
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
    return ProgramModule(
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
    from .module import ProgramModule

    if isinstance(program, ProgramModule):
        return program
    return program_module_from_program_dict(program)


def program_dict_view(program: ProgramModule | Mapping[str, Any]) -> dict[str, Any]:
    return program_module_to_state_dict(ensure_program_module(program))


__all__ = [
    "PROGRAM_MODULE_SCHEMA_ID",
    "ensure_program_module",
    "program_dict_view",
    "program_module_from_payload",
    "program_module_from_program_dict",
    "program_module_to_payload",
    "program_module_to_program_dict",
    "program_module_to_state_dict",
]
