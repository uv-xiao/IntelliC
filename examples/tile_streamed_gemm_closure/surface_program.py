from __future__ import annotations

from dataclasses import replace
from typing import Any

from htp.ir.interpreters.entrypoints import NODE_PROGRAM_INTERPRETER_ID
from htp.ir.program.build import build_tile_streamed_gemm_core_module
from htp.ir.program.module import ProgramEntrypoint, ProgramModule

PROGRAM_MODULE = replace(
    build_tile_streamed_gemm_core_module(),
    entrypoints=(ProgramEntrypoint(name="run", interpreter_id=NODE_PROGRAM_INTERPRETER_ID),),
    meta={"variant": "surface"},
)


def program_module() -> ProgramModule:
    return PROGRAM_MODULE


def run(*args: Any, **kwargs: Any) -> Any:
    return PROGRAM_MODULE.run(*args, **kwargs)
