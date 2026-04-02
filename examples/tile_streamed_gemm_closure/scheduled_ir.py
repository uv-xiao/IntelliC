from __future__ import annotations

from typing import Any

from htp.ir.program.module import ProgramModule
from htp.passes.enrich_protocol import enrich_schedule_and_protocol
from htp.passes.tile_and_stage import tile_and_stage_rewrite

from .core_ir import PROGRAM_MODULE as CORE_PROGRAM_MODULE

PROGRAM_MODULE = enrich_schedule_and_protocol(tile_and_stage_rewrite(CORE_PROGRAM_MODULE))


def program_module() -> ProgramModule:
    return PROGRAM_MODULE


def run(*args: Any, **kwargs: Any) -> Any:
    return PROGRAM_MODULE.run(*args, **kwargs)
