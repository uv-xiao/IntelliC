from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.ir.program.module import ProgramModule, program_dict_view
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import apply_software_pipeline_plan, stage_payloads_from_program
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::apply_software_pipeline@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="transform",
    ast_effect="mutates",
    requires=("Analysis.SoftwarePipelinePlan@1", "Schedule.WarpSpecialized@1"),
    provides=("Schedule.SoftwarePipelined@1",),
    outputs=("ir.ast", "ir.schedule"),
)


def run(
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    del stage_before

    next_program = deepcopy(program_dict_view(program))
    next_schedule, next_scheduled_ops = apply_software_pipeline_plan(
        next_program.get("schedule", {}),
        next_program.get("scheduled_ops", ()),
        pipeline_plan=next_program.get("analysis", {}).get("software_pipeline", {}),
    )
    next_program["schedule"] = next_schedule
    next_program["scheduled_ops"] = next_scheduled_ops
    next_module = ProgramModule.from_program_dict(next_program)
    stage_payloads = stage_payloads_from_program(next_module)
    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves", modes=("sim",), program_text=render_program_state_module(next_module)
        ),
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"schedule_hash": "demo-software-pipelined-v1"},
        time_ms=0.2,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
