from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..core.analysis import AnalysisRecord
from ..interpreters.registry import run_program_module
from .components import (
    ProgramAspects,
    ProgramEntrypoint,
    ProgramIdentity,
    ProgramItems,
    normalize_analyses,
)
from .serialization import (
    PROGRAM_MODULE_SCHEMA_ID,
    ensure_program_module,
    program_dict_view,
    program_module_from_payload,
    program_module_from_program_dict,
    program_module_to_payload,
    program_module_to_program_dict,
    program_module_to_state_dict,
)


@dataclass(frozen=True)
class ProgramModule:
    items: ProgramItems
    aspects: ProgramAspects
    analyses: dict[str, AnalysisRecord | Mapping[str, Any]] = field(default_factory=dict)
    identity: ProgramIdentity = field(default_factory=lambda: ProgramIdentity(entities={}, bindings={}))
    entrypoints: tuple[ProgramEntrypoint, ...] = (ProgramEntrypoint("run"),)
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "analyses", normalize_analyses(self.analyses))

    def to_payload(self) -> dict[str, Any]:
        return program_module_to_payload(self)

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
        return program_module_to_program_dict(self)

    def to_state_dict(self) -> dict[str, Any]:
        return program_module_to_state_dict(self)

    @classmethod
    def from_program_dict(
        cls,
        program: Mapping[str, Any],
        *,
        analyses: Mapping[str, Mapping[str, Any]] | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> ProgramModule:
        return program_module_from_program_dict(program, analyses=analyses, meta=meta)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ProgramModule:
        return program_module_from_payload(payload)

    @classmethod
    def compose(
        cls,
        *modules: ProgramModule,
        canonical_program: Mapping[str, Any],
        source_surface: str,
        entry: str = "run",
        routine: Mapping[str, Any] | None = None,
        interpreter_id: str | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> ProgramModule:
        from .compose import compose_program_modules

        if interpreter_id is None:
            return compose_program_modules(
                *modules,
                canonical_program=canonical_program,
                source_surface=source_surface,
                entry=entry,
                routine=routine,
                meta=meta,
            )
        return compose_program_modules(
            *modules,
            canonical_program=canonical_program,
            source_surface=source_surface,
            entry=entry,
            routine=routine,
            interpreter_id=interpreter_id,
            meta=meta,
        )


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
