from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import AnalysisOutput, PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import build_software_pipeline_plan, stage_payloads_from_program
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::analyze_software_pipeline@1"
ANALYSIS_ID = "htp::PipelinePlan@1"
ANALYSIS_SCHEMA = "htp.analysis.pipeline_plan.v1"
ANALYSIS_PATH = "analysis/pipeline_plan.json"

CONTRACT = PassContract.analysis(
    pass_id=PASS_ID,
    owner="htp",
    requires=("Analysis.SchedulePlan@1", "Analysis.WarpRolePlan@1"),
    provides=("Analysis.SoftwarePipelinePlan@1",),
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

    next_program = deepcopy(dict(program))
    pipeline_plan = build_software_pipeline_plan(
        entry=next_program["entry"],
        schedule_plan=next_program.get("analysis", {}).get("schedule", {}),
        warp_role_plan=next_program.get("analysis", {}).get("warp_role_plan", {}),
        kernel_ir=next_program.get("kernel_ir", {}),
    )
    analysis_state = dict(next_program.get("analysis", {}))
    analysis_state["software_pipeline"] = pipeline_plan
    next_program["analysis"] = analysis_state
    stage_payloads = stage_payloads_from_program(next_program)
    return next_program, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves", modes=("sim",), program_text=render_program_state_module(next_program)
        ),
        analyses={ANALYSIS_PATH: pipeline_plan},
        entities_payload=stage_payloads["entities_payload"],
        bindings_payload=stage_payloads["bindings_payload"],
        program_ast_payload=stage_payloads["program_ast_payload"],
        kernel_ir_payload=stage_payloads["kernel_ir_payload"],
        workload_ir_payload=stage_payloads["workload_ir_payload"],
        types_payload=stage_payloads["types_payload"],
        layout_payload=stage_payloads["layout_payload"],
        effects_payload=stage_payloads["effects_payload"],
        schedule_payload=stage_payloads["schedule_payload"],
        digests={"analysis_hash": "demo-software-pipeline-plan-v1"},
        time_ms=0.2,
    )


__all__ = ["ANALYSIS_ID", "ANALYSIS_PATH", "ANALYSIS_SCHEMA", "CONTRACT", "PASS_ID", "run"]
