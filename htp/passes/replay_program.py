from __future__ import annotations

from pprint import pformat
from typing import Any

from htp.passes.program_model import snapshot_program


def render_program_state_module(program: dict[str, Any]) -> str:
    return "\n".join(
        (
            "PROGRAM_STATE = " + pformat(snapshot_program(program), width=88, sort_dicts=True),
            "",
            "def run(*args, **kwargs):",
            "    del args, kwargs",
            "    return PROGRAM_STATE",
            "",
        )
    )


__all__ = ["render_program_state_module"]
