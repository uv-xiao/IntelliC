from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from htp.passes import (
    analyze_async_resources,
    analyze_loop_dependencies,
    analyze_schedule,
    analyze_software_pipeline,
    analyze_warp_specialization,
    apply_schedule,
    apply_software_pipeline,
    apply_warp_specialization,
    ast_canonicalize,
    emit_package,
    semantic_model,
    typecheck_layout_effects,
)
from htp.passes.contracts import PassContract
from htp_ext.registry import active_extensions


@dataclass(frozen=True)
class RegisteredPass:
    contract: PassContract
    run: Any


def core_passes() -> tuple[RegisteredPass, ...]:
    return (
        RegisteredPass(contract=ast_canonicalize.CONTRACT, run=ast_canonicalize.run),
        RegisteredPass(contract=semantic_model.CONTRACT, run=semantic_model.run),
        RegisteredPass(contract=typecheck_layout_effects.CONTRACT, run=typecheck_layout_effects.run),
        RegisteredPass(contract=analyze_loop_dependencies.CONTRACT, run=analyze_loop_dependencies.run),
        RegisteredPass(contract=analyze_async_resources.CONTRACT, run=analyze_async_resources.run),
        RegisteredPass(contract=analyze_schedule.CONTRACT, run=analyze_schedule.run),
        RegisteredPass(contract=apply_schedule.CONTRACT, run=apply_schedule.run),
        RegisteredPass(contract=analyze_warp_specialization.CONTRACT, run=analyze_warp_specialization.run),
        RegisteredPass(contract=apply_warp_specialization.CONTRACT, run=apply_warp_specialization.run),
        RegisteredPass(contract=analyze_software_pipeline.CONTRACT, run=analyze_software_pipeline.run),
        RegisteredPass(contract=apply_software_pipeline.CONTRACT, run=apply_software_pipeline.run),
        RegisteredPass(contract=emit_package.CONTRACT, run=emit_package.run),
    )


def extension_passes(*, program: Mapping[str, Any]) -> tuple[RegisteredPass, ...]:
    passes: list[RegisteredPass] = []
    for extension in active_extensions(program):
        passes.extend(extension.registered_passes())
    return tuple(passes)


def registered_passes(*, program: Mapping[str, Any]) -> tuple[RegisteredPass, ...]:
    return core_passes() + extension_passes(program=program)


def resolve_passes(
    pass_ids: tuple[str, ...] | list[str],
    *,
    program: Mapping[str, Any],
) -> tuple[RegisteredPass, ...]:
    registry = {entry.contract.pass_id: entry for entry in registered_passes(program=program)}
    missing = [pass_id for pass_id in pass_ids if pass_id not in registry]
    if missing:
        raise ValueError(f"Unknown registered pass id(s): {', '.join(missing)}")
    return tuple(registry[pass_id] for pass_id in pass_ids)


__all__ = ["RegisteredPass", "core_passes", "extension_passes", "registered_passes", "resolve_passes"]
