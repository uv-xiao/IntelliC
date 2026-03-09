from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
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
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    next_schedule, next_scheduled_ops = apply_software_pipeline_plan(
        next_program.get("schedule", {}),
        next_program.get("scheduled_ops", ()),
        pipeline_plan=next_program.get("analysis", {}).get("software_pipeline", {}),
    )
    next_program["schedule"] = next_schedule
    next_program["scheduled_ops"] = next_scheduled_ops
    stage_payloads = stage_payloads_from_program(next_program)
    return next_program, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves", modes=("sim",), program_text=render_program_state_module(next_program)
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
        digests={"schedule_hash": "demo-software-pipelined-v1"},
        time_ms=0.2,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
