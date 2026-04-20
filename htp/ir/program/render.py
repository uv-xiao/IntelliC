from __future__ import annotations

from pprint import pformat


def _payload_assignment(name: str, value: object) -> str:
    return f"{name} = {pformat(value, width=100, sort_dicts=False)}"


def render_program_module_payload(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            '"""Readable staged Python snapshot for HTP replay and debugging."""',
            "",
            "from htp.ir.program.module import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems, ProgramModule",
            "",
            _payload_assignment("ITEMS_PAYLOAD", payload["items"]),
            "_ITEMS = ProgramItems(**ITEMS_PAYLOAD)",
            "",
            _payload_assignment("ASPECTS_PAYLOAD", payload["aspects"]),
            "_ASPECTS = ProgramAspects(**ASPECTS_PAYLOAD)",
            "",
            _payload_assignment("IDENTITY_PAYLOAD", payload["identity"]),
            "_IDENTITY = ProgramIdentity(**IDENTITY_PAYLOAD)",
            "",
            _payload_assignment("ENTRYPOINTS_PAYLOAD", payload["entrypoints"]),
            "_ENTRYPOINTS = tuple(ProgramEntrypoint(**item) for item in ENTRYPOINTS_PAYLOAD)",
            "",
            _payload_assignment("ANALYSES", payload["analyses"]),
            _payload_assignment("META", payload["meta"]),
            "",
            "PROGRAM_MODULE = ProgramModule(",
            "    items=_ITEMS,",
            "    aspects=_ASPECTS,",
            "    analyses=ANALYSES,",
            "    identity=_IDENTITY,",
            "    entrypoints=_ENTRYPOINTS,",
            "    meta=META,",
            ")",
            "",
            "def program_module():",
            '    """Return the typed ProgramModule for this staged artifact."""',
            "    return PROGRAM_MODULE",
            "",
            "def program_state():",
            '    """Return the compatibility snapshot payload for this staged artifact."""',
            "    return PROGRAM_MODULE.to_program_dict()",
            "",
            "def run(*args, mode='sim', runtime=None, trace=None, **kwargs):",
            '    """Execute this staged ProgramModule through its registered interpreter."""',
            "    return PROGRAM_MODULE.run(*args, entry='run', mode=mode, runtime=runtime, trace=trace, **kwargs)",
            "",
        ]
    )


__all__ = ["render_program_module_payload"]
