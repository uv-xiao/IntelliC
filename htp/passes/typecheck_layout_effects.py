from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.artifacts.state import state_ref
from htp.compiler_errors import CompilerDiagnosticError
from htp.ir.module import ProgramModule, program_dict_view
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import build_type_layout_effects, normalize_target, stage_payloads_from_program
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::typecheck_layout_effects@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="mixed",
    ast_effect="preserves",
    requires=("Semantic.ModelBuilt@1",),
    provides=(
        "Type.LayoutChecked@1",
        "Type.EffectsChecked@1",
    ),
    establishes_layout_invariants=("Layout.Typed@1",),
    establishes_effect_invariants=("Effects.Typed@1", "Effects.ProtocolBalanced@1"),
    outputs=("ir.types", "ir.layout", "ir.effects"),
)


def run(
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    next_program = deepcopy(program_dict_view(program))
    try:
        types, layout, effects = build_type_layout_effects(
            next_program.get("kernel_ir", {}),
            next_program.get("workload_ir", {}),
            target=normalize_target(next_program),
        )
    except CompilerDiagnosticError as exc:
        raise _resolve_compiler_diagnostic(exc, stage_before=stage_before) from None
    next_program["types"] = types
    next_program["layout"] = layout
    next_program["effects"] = effects
    next_module = ProgramModule.from_program_dict(next_program)
    stage_payloads = stage_payloads_from_program(next_module)

    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_module),
        ),
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"types_hash": "demo-types-v2", "effects_hash": "demo-effects-v2"},
        time_ms=0.3,
    )


def _resolve_compiler_diagnostic(
    exc: CompilerDiagnosticError, *, stage_before: Mapping[str, object]
) -> CompilerDiagnosticError:
    payload_ref = exc.payload_ref
    if payload_ref is None and exc.payload_ref_hint is not None:
        payload_ref = _resolve_payload_ref_hint(exc.payload_ref_hint, stage_before=stage_before)
    return exc.with_context(
        stage_id=str(stage_before.get("id", "")),
        pass_id=PASS_ID,
        payload_ref=payload_ref,
    )


def _resolve_payload_ref_hint(hint: str, *, stage_before: Mapping[str, object]) -> str | None:
    if hint.startswith("semantic."):
        semantic_key = hint.partition(".")[2]
        stage_id = stage_before.get("id")
        if isinstance(stage_id, str):
            pointer = {
                "kernel_ir": "/items/kernel_ir",
                "workload_ir": "/items/workload_ir",
                "types": "/aspects/types",
                "layout": "/aspects/layout",
                "effects": "/aspects/effects",
                "schedule": "/aspects/schedule",
            }.get(semantic_key)
            if pointer is not None:
                return state_ref({"stages": {"graph": [stage_before]}}, stage_id, pointer)
    if hint == "analysis.index":
        relpath = stage_before.get("stage")
        if isinstance(relpath, str):
            return f"{relpath}#/analysis_inventory"
    stage_dir = stage_before.get("dir")
    if isinstance(stage_dir, str):
        return Path(stage_dir).as_posix()
    return None


__all__ = ["CONTRACT", "PASS_ID", "run"]
