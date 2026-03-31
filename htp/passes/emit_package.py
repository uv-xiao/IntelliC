from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.ir.module import ProgramModule, program_dict_view
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
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    del stage_before

    next_program = deepcopy(program_dict_view(program))
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
    next_module = ProgramModule.from_program_dict(next_program)
    stage_payloads = stage_payloads_from_program(next_module)

    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_module),
        ),
        program_module_payload=stage_payloads["program_module_payload"],
        time_ms=0.1,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
