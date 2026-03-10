from __future__ import annotations

import keyword
from pprint import pformat
from typing import Any

from htp.passes.program_model import snapshot_program


def render_program_state_module(program: dict[str, Any]) -> str:
    program_state = snapshot_program(program)
    bindings = _render_bindings(program_state)
    state_items = "\n".join(f"    {key!r}: {name}," for key, name in bindings)
    body = [
        '"""Readable staged Python snapshot for HTP replay and debugging."""',
        "",
    ]
    for key, name in bindings:
        body.append(f"# {key}")
        body.append(_render_assignment(name, program_state[key]))
        body.append("")
    body.extend(
        [
            "PROGRAM_STATE = {",
            state_items,
            "}",
            "",
            "def run(*args, **kwargs):",
            '    """Return the staged program payload for replay in sim mode."""',
            "    del args, kwargs",
            "    return PROGRAM_STATE",
            "",
        ]
    )
    return "\n".join(body)


def _render_bindings(program_state: dict[str, Any]) -> list[tuple[str, str]]:
    bindings: list[tuple[str, str]] = []
    used_names: set[str] = set()
    for index, key in enumerate(program_state):
        candidate = _binding_name_for_key(key)
        if not candidate:
            candidate = f"FIELD_{index:02d}"
        suffix = 0
        base_name = candidate
        while candidate in used_names:
            suffix += 1
            candidate = f"{base_name}_{suffix}"
        bindings.append((key, candidate))
        used_names.add(candidate)
    return bindings


def _binding_name_for_key(key: str) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in key).strip("_")
    if not normalized:
        return ""
    if normalized[0].isdigit():
        normalized = f"FIELD_{normalized}"
    normalized = normalized.upper()
    if keyword.iskeyword(normalized.lower()):
        normalized = f"{normalized}_FIELD"
    return normalized


def _render_assignment(name: str, value: Any) -> str:
    rendered = pformat(value, width=88, sort_dicts=False)
    if "\n" not in rendered:
        return f"{name} = {rendered}"
    indented = "\n".join(f"    {line}" for line in rendered.splitlines())
    return f"{name} = (\n{indented}\n)"


__all__ = ["render_program_state_module"]
