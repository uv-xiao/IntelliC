from __future__ import annotations

from pprint import pformat
from typing import Any


def render_program_state_module(program: dict[str, Any]) -> str:
    return "\n".join(
        (
            "PROGRAM_STATE = " + pformat(program, width=88, sort_dicts=True),
            "",
            "def run(*args, **kwargs):",
            "    del args, kwargs",
            "    return PROGRAM_STATE",
            "",
        )
    )


__all__ = ["render_program_state_module"]
