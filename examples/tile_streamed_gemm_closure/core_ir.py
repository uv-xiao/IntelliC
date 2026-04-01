from __future__ import annotations

from typing import Any

from htp.ir.program.module import ProgramModule
from htp.passes.surface_to_core import surface_to_core_normalize

from .surface_program import PROGRAM_MODULE as SURFACE_PROGRAM_MODULE

PROGRAM_MODULE = surface_to_core_normalize(SURFACE_PROGRAM_MODULE)


def program_module() -> ProgramModule:
    return PROGRAM_MODULE


def run(*args: Any, **kwargs: Any) -> Any:
    return PROGRAM_MODULE.run(*args, **kwargs)
