from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import build_semantic_model, stage_payloads_from_program
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::semantic_model@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="mixed",
    ast_effect="preserves",
    requires=("Invariant.ASTCanonical@1",),
    provides=("Semantic.ModelBuilt@1",),
    outputs=("ir.kernel", "ir.workload", "ids.entities", "ids.bindings"),
)


def run(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    kernel_ir, workload_ir, entities_payload, bindings_payload = build_semantic_model(
        next_program["canonical_ast"]
    )
    next_program["schedule_directives"] = dict(next_program["canonical_ast"].get("schedule_directives", {}))
    next_program["kernel_ir"] = kernel_ir
    next_program["workload_ir"] = workload_ir
    next_program["entities_payload"] = entities_payload
    next_program["bindings_payload"] = bindings_payload
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
        digests={"ast_hash": "semantic-model-v1"},
        time_ms=0.3,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
