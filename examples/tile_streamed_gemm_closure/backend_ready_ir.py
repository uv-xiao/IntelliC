from __future__ import annotations

from typing import Any

from htp.ir.program.module import ProgramModule
from htp.passes.backend_ready import backend_ready_rewrite

from .scheduled_ir import PROGRAM_MODULE as SCHEDULED_PROGRAM_MODULE

PROGRAM_MODULE = backend_ready_rewrite(SCHEDULED_PROGRAM_MODULE)


def program_module() -> ProgramModule:
    return PROGRAM_MODULE


def run(*args: Any, **kwargs: Any) -> Any:
    return PROGRAM_MODULE.run(*args, **kwargs)
