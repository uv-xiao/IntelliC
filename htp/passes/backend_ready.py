"""Backend-ready committed variant rewrite for the closure-proof pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.ir.interpreters.entrypoints import NODE_PROGRAM_INTERPRETER_ID
from htp.ir.program.module import ProgramModule
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult
from htp.passes.program_model import stage_payloads_from_program
from htp.passes.program_variants import clone_program_variant
from htp.passes.replay_program import render_program_state_module

PASS_ID = "htp::backend_ready@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="transform",
    ast_effect="mutates",
    requires=("Proof.TileStreamedGEMM.ProtocolIR@1",),
    provides=("Proof.TileStreamedGEMM.BackendReadyIR@1",),
    outputs=("ir.program_module", "ir.schedule"),
)


def backend_ready_rewrite(program: ProgramModule | Mapping[str, Any]) -> ProgramModule:
    return clone_program_variant(
        program,
        variant="backend_ready",
        schedule_updates={"backend_ready": True},
        meta_updates={"backend_target": "closure-proof"},
        interpreter_id=NODE_PROGRAM_INTERPRETER_ID,
    )


def run(
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    del stage_before
    next_module = backend_ready_rewrite(program)
    stage_payloads = stage_payloads_from_program(next_module)
    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_module),
        ),
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"variant": "backend_ready"},
        time_ms=0.1,
    )


__all__ = ["CONTRACT", "PASS_ID", "backend_ready_rewrite", "run"]
