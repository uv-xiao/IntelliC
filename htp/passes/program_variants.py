"""Helpers for typed ProgramModule variant rewrites."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.ir.program.module import ProgramEntrypoint, ProgramModule, ensure_program_module, program_dict_view


def clone_program_variant(
    program: ProgramModule | Mapping[str, Any],
    *,
    variant: str,
    schedule_updates: Mapping[str, Any] | None = None,
    effect_updates: Mapping[str, Any] | None = None,
    meta_updates: Mapping[str, Any] | None = None,
    interpreter_id: str | None = None,
) -> ProgramModule:
    """Clone one committed `ProgramModule` while updating variant-level state."""

    module = ensure_program_module(program)
    next_program = deepcopy(program_dict_view(module))
    next_program["meta"] = {
        **dict(next_program.get("meta", {})),
        "variant": variant,
        **dict(meta_updates or {}),
    }
    next_program["schedule"] = {
        "schema": "htp.schedule.v1",
        **dict(next_program.get("schedule", {})),
        **dict(schedule_updates or {}),
    }
    next_program["effects"] = {
        "schema": "htp.effects.v1",
        **dict(next_program.get("effects", {})),
        **dict(effect_updates or {}),
    }
    if interpreter_id is not None:
        next_program["entrypoints"] = [
            ProgramEntrypoint(name="run", interpreter_id=interpreter_id).__dict__,
        ]
    return ProgramModule.from_program_dict(next_program)


__all__ = ["clone_program_variant"]
