from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import AnalysisOutput, PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import build_schedule_plan, normalize_target, stage_payloads_from_program
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::analyze_schedule@1"
ANALYSIS_ID = "htp::SchedulePlan@1"
ANALYSIS_SCHEMA = "htp.analysis.schedule_plan.v1"
ANALYSIS_PATH = "analysis/schedule_plan.json"

CONTRACT = PassContract.analysis(
    pass_id=PASS_ID,
    owner="htp",
    requires=("Type.LayoutChecked@1", "Type.EffectsChecked@1"),
    provides=("Analysis.SchedulePlan@1",),
    analysis_produces=(
        AnalysisOutput(
            analysis_id=ANALYSIS_ID,
            schema=ANALYSIS_SCHEMA,
            path_hint=ANALYSIS_PATH,
        ),
    ),
    outputs=("analysis.index", "analysis.result"),
)


def run(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    schedule_plan = build_schedule_plan(
        entry=program["entry"],
        kernel_ir=program.get("kernel_ir", {}),
        effects=program.get("effects", {}),
        target=normalize_target(program),
    )

    next_program = deepcopy(dict(program))
    analysis_state = dict(next_program.get("analysis", {}))
    analysis_state["schedule"] = schedule_plan
    next_program["analysis"] = analysis_state
    stage_payloads = stage_payloads_from_program(next_program)

    return next_program, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_program),
        ),
        analyses={ANALYSIS_PATH: schedule_plan},
        entities_payload=stage_payloads["entities_payload"],
        bindings_payload=stage_payloads["bindings_payload"],
        program_ast_payload=stage_payloads["program_ast_payload"],
        kernel_ir_payload=stage_payloads["kernel_ir_payload"],
        workload_ir_payload=stage_payloads["workload_ir_payload"],
        types_payload=stage_payloads["types_payload"],
        layout_payload=stage_payloads["layout_payload"],
        effects_payload=stage_payloads["effects_payload"],
        schedule_payload=stage_payloads["schedule_payload"],
        digests={"analysis_hash": "demo-schedule-plan-v1"},
        time_ms=0.4,
    )


__all__ = ["ANALYSIS_ID", "ANALYSIS_PATH", "ANALYSIS_SCHEMA", "CONTRACT", "PASS_ID", "run"]
