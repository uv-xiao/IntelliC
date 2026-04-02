"""Schedule/protocol enrichment pass for the closure-proof GEMM pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.ir.program.module import ProgramModule
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import stage_payloads_from_program
from htp.passes.program_variants import clone_program_variant
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::enrich_schedule_and_protocol@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="transform",
    ast_effect="preserves",
    requires=("Proof.TileStreamedGEMM.ScheduledIR@1",),
    provides=("Proof.TileStreamedGEMM.ProtocolIR@1",),
    outputs=("ir.program_module", "ir.effects", "ir.schedule"),
)


def enrich_schedule_and_protocol(program: ProgramModule | Mapping[str, Any]) -> ProgramModule:
    return clone_program_variant(
        program,
        variant="scheduled",
        schedule_updates={
            "protocol_roles": (
                {"task": "load_tiles", "role": "producer"},
                {"task": "mma_tiles", "role": "consumer"},
            ),
        },
        effect_updates={
            "protocols": ({"channel": "tile_stream", "protocol": "fifo", "capacity": 2},),
        },
    )


def run(
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    del stage_before
    next_module = enrich_schedule_and_protocol(program)
    stage_payloads = stage_payloads_from_program(next_module)
    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_module),
        ),
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"variant": "scheduled-protocol"},
        time_ms=0.1,
    )


__all__ = ["CONTRACT", "PASS_ID", "enrich_schedule_and_protocol", "run"]
