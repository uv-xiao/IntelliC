from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import build_type_layout_effects, normalize_target
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::typecheck_layout_effects@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="mixed",
    ast_effect="preserves",
    requires=("Invariant.ASTCanonical@1",),
    provides=(
        "Type.LayoutChecked@1",
        "Type.EffectsChecked@1",
    ),
    outputs=("ir.types", "ir.layout", "ir.effects"),
)


def run(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    canonical_ast = next_program.get("canonical_ast", {})
    canonical_ops = canonical_ast.get("ops", ())
    types, layout, effects = build_type_layout_effects(
        canonical_ops,
        target=normalize_target(next_program),
    )
    next_program["types"] = types
    next_program["layout"] = layout
    next_program["effects"] = effects

    return next_program, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_program),
        ),
        digests={
            "types_hash": "demo-types-v2",
            "effects_hash": "demo-effects-v2",
        },
        time_ms=0.3,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
