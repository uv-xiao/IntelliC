from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.ir.program.module import ProgramModule, program_dict_view
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
    analysis_requires=("Analysis.LoopDeps@1", "Analysis.AsyncResourceChecks@1"),
    requires_layout_invariants=("Layout.Typed@1",),
    requires_effect_invariants=("Effects.Typed@1", "Effects.ProtocolBalanced@1"),
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
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    del stage_before

    current = program_dict_view(program)
    schedule_plan = build_schedule_plan(
        entry=current["entry"],
        kernel_ir=current.get("kernel_ir", {}),
        effects=current.get("effects", {}),
        target=normalize_target(current),
        schedule_directives=current.get("schedule_directives", {}),
    )

    next_program = deepcopy(current)
    analysis_state = dict(next_program.get("analysis", {}))
    analysis_state["schedule"] = schedule_plan
    next_program["analysis"] = analysis_state
    next_module = ProgramModule.from_program_dict(next_program)
    stage_payloads = stage_payloads_from_program(next_module)

    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_module),
        ),
        analyses={ANALYSIS_PATH: schedule_plan},
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"analysis_hash": "demo-schedule-plan-v1"},
        time_ms=0.4,
    )


__all__ = ["ANALYSIS_ID", "ANALYSIS_PATH", "ANALYSIS_SCHEMA", "CONTRACT", "PASS_ID", "run"]
