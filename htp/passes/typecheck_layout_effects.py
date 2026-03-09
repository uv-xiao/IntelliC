from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
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
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    types, layout, effects = build_type_layout_effects(
        next_program.get("kernel_ir", {}),
        next_program.get("workload_ir", {}),
        target=normalize_target(next_program),
    )
    next_program["types"] = types
    next_program["layout"] = layout
    next_program["effects"] = effects
    stage_payloads = stage_payloads_from_program(next_program)

    return next_program, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_program),
        ),
        entities_payload=stage_payloads["entities_payload"],
        bindings_payload=stage_payloads["bindings_payload"],
        program_ast_payload=stage_payloads["program_ast_payload"],
        kernel_ir_payload=stage_payloads["kernel_ir_payload"],
        workload_ir_payload=stage_payloads["workload_ir_payload"],
        types_payload=stage_payloads["types_payload"],
        layout_payload=stage_payloads["layout_payload"],
        effects_payload=stage_payloads["effects_payload"],
        schedule_payload=stage_payloads["schedule_payload"],
        digests={"types_hash": "demo-types-v2", "effects_hash": "demo-effects-v2"},
        time_ms=0.3,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
