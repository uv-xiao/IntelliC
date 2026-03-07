from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import AnalysisOutput, PassContract
from htp.passes.manager import PassResult

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

    ticks = [
        {
            "tick": tick,
            "op": op_name,
        }
        for tick, op_name in enumerate(program["ops"])
    ]
    schedule_plan = {
        "schema": ANALYSIS_SCHEMA,
        "entry": program["entry"],
        "ticks": ticks,
    }

    next_program = deepcopy(dict(program))
    analysis_state = dict(next_program.get("analysis", {}))
    analysis_state["schedule"] = schedule_plan
    next_program["analysis"] = analysis_state

    return next_program, PassResult(
        runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        analyses={
            ANALYSIS_PATH: schedule_plan,
        },
        digests={"analysis_hash": "demo-schedule-plan-v1"},
        time_ms=0.4,
    )


__all__ = [
    "ANALYSIS_ID",
    "ANALYSIS_PATH",
    "ANALYSIS_SCHEMA",
    "CONTRACT",
    "PASS_ID",
    "run",
]
