from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.ir.program.module import ProgramModule, program_dict_view
from htp.passes.contracts import AnalysisOutput, PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import build_warp_role_plan, normalize_target, stage_payloads_from_program
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::analyze_warp_specialization@1"
ANALYSIS_ID = "htp::WarpRolePlan@1"
ANALYSIS_SCHEMA = "htp.analysis.warp_role_plan.v1"
ANALYSIS_PATH = "analysis/warp_role_plan.json"

CONTRACT = PassContract.analysis(
    pass_id=PASS_ID,
    owner="htp",
    requires=("Analysis.SchedulePlan@1",),
    requires_layout_invariants=("Layout.Typed@1",),
    requires_effect_invariants=("Effects.Typed@1",),
    provides=("Analysis.WarpRolePlan@1",),
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

    next_program = deepcopy(program_dict_view(program))
    warp_role_plan = build_warp_role_plan(
        entry=next_program["entry"],
        kernel_ir=next_program.get("kernel_ir", {}),
        target=normalize_target(next_program),
        schedule_directives=next_program.get("schedule_directives", {}),
    )
    analysis_state = dict(next_program.get("analysis", {}))
    analysis_state["warp_role_plan"] = warp_role_plan
    next_program["analysis"] = analysis_state
    next_module = ProgramModule.from_program_dict(next_program)
    stage_payloads = stage_payloads_from_program(next_module)

    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves", modes=("sim",), program_text=render_program_state_module(next_module)
        ),
        analyses={ANALYSIS_PATH: warp_role_plan},
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"analysis_hash": "demo-warp-role-plan-v1"},
        time_ms=0.2,
    )


__all__ = ["ANALYSIS_ID", "ANALYSIS_PATH", "ANALYSIS_SCHEMA", "CONTRACT", "PASS_ID", "run"]
