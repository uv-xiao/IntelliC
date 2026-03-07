from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import scheduled_ops_from_plan
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::apply_schedule@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="transform",
    ast_effect="mutates",
    requires=("Analysis.SchedulePlan@1",),
    provides=("Schedule.Applied@1",),
    outputs=("ir.ast", "ir.schedule"),
)


def run(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    schedule_plan = dict(next_program["analysis"]["schedule"])
    scheduled_ops = scheduled_ops_from_plan(schedule_plan)
    next_program["schedule"] = {
        "applied": True,
        "ticks": list(schedule_plan["ticks"]),
        "pipeline_depth": schedule_plan["pipeline_depth"],
        "ordered_ops": [op["op_id"] for op in scheduled_ops],
    }
    next_program["scheduled_ops"] = scheduled_ops

    return next_program, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_program),
        ),
        digests={"ast_hash": "demo-scheduled-ast-v2"},
        time_ms=0.2,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
