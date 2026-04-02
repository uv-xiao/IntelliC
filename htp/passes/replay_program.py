from __future__ import annotations

from collections.abc import Mapping

from htp.ir.program.module import ProgramModule, ensure_program_module
from htp.ir.program.render import render_program_module_payload


def render_program_state_module(program: ProgramModule | Mapping[str, object]) -> str:
    module = ensure_program_module(program)
    return render_program_module_payload(module.to_payload())


__all__ = ["render_program_state_module"]
