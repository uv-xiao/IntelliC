from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import stage_payloads_from_program
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::emit_package@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="mixed",
    ast_effect="preserves",
    requires=("Schedule.Applied@1",),
    provides=("Package.Emitted@1",),
    outputs=("manifest", "package"),
)


def run(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    next_program["package"] = {
        "emitted": True,
        "entry": next_program["entry"],
        "entrypoint": next_program["entry"],
        "kernel_entry": next_program.get("kernel_ir", {}).get("entry", next_program["entry"]),
        "target_backend": next_program.get("target", {}).get("backend", "generic"),
        "scheduled_tick_count": len(next_program.get("schedule", {}).get("ticks", ())),
        "has_barrier": any(
            tick.get("op") == "barrier"
            for tick in next_program.get("schedule", {}).get("ticks", ())
            if isinstance(tick, Mapping)
        ),
    }
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
        time_ms=0.1,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
