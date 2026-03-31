from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.ir.module import ProgramModule, program_dict_view
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import scheduled_ops_from_plan, stage_payloads_from_program
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
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    del stage_before

    next_program = deepcopy(program_dict_view(program))
    schedule_plan = dict(next_program["analysis"]["schedule"])
    scheduled_ops = scheduled_ops_from_plan(schedule_plan)
    next_program["schedule"] = {
        "schema": "htp.schedule.v1",
        "applied": True,
        "ticks": list(schedule_plan["ticks"]),
        "pipeline_depth": schedule_plan["pipeline_depth"],
        "ordered_ops": [op["op_id"] for op in scheduled_ops],
        "directives": dict(schedule_plan.get("directives", {})),
        "buffering_strategy": str(schedule_plan.get("buffering_strategy", "single")),
        "launch": dict(schedule_plan.get("launch", {})),
        "warp_role_plan": dict(schedule_plan.get("warp_role_plan", {})),
        "legality": dict(schedule_plan.get("legality", {})),
    }
    next_program["scheduled_ops"] = scheduled_ops
    next_module = ProgramModule.from_program_dict(next_program)
    stage_payloads = stage_payloads_from_program(next_module)

    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_module),
        ),
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"ast_hash": "demo-scheduled-ast-v2"},
        time_ms=0.2,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
