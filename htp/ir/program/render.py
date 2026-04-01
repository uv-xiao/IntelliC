from __future__ import annotations


def render_program_module_payload(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            '"""Readable staged Python snapshot for HTP replay and debugging."""',
            "",
            "from htp.ir.program.module import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems, ProgramModule",
            "",
            f"ITEMS = ProgramItems(**{repr(payload['items'])})",
            f"ASPECTS = ProgramAspects(**{repr(payload['aspects'])})",
            f"IDENTITY = ProgramIdentity(**{repr(payload['identity'])})",
            f"ENTRYPOINTS = tuple(ProgramEntrypoint(**item) for item in {repr(payload['entrypoints'])})",
            f"ANALYSES = {repr(payload['analyses'])}",
            f"META = {repr(payload['meta'])}",
            "",
            "PROGRAM_MODULE = ProgramModule(",
            "    items=ITEMS,",
            "    aspects=ASPECTS,",
            "    analyses=ANALYSES,",
            "    identity=IDENTITY,",
            "    entrypoints=ENTRYPOINTS,",
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
