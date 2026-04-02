"""Surface-to-core normalization pass for the closure-proof ProgramModule flow."""

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

PASS_ID = "htp::surface_to_core@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="transform",
    ast_effect="preserves",
    provides=("Proof.TileStreamedGEMM.CoreIR@1",),
    outputs=("ir.program_module",),
)


def surface_to_core_normalize(program: ProgramModule | Mapping[str, Any]) -> ProgramModule:
    return clone_program_variant(
        program,
        variant="core",
        interpreter_id=NODE_PROGRAM_INTERPRETER_ID,
    )


def run(
    program: ProgramModule | Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[ProgramModule, PassResult]:
    del stage_before
    next_module = surface_to_core_normalize(program)
    stage_payloads = stage_payloads_from_program(next_module)
    return next_module, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=render_program_state_module(next_module),
        ),
        program_module_payload=stage_payloads["program_module_payload"],
        digests={"variant": "core"},
        time_ms=0.1,
    )


__all__ = ["CONTRACT", "PASS_ID", "run", "surface_to_core_normalize"]
