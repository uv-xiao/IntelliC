from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from examples.tile_streamed_gemm_closure import (
    backend_ready_ir,
    core_ir,
    scheduled_ir,
    surface_program,
)
from htp.ir.program.module import ProgramModule
from htp.passes.replay_program import render_program_state_module


def _import_rendered_module(tmp_path: Path, module: ProgramModule) -> ModuleType:
    program_path = tmp_path / f"{uuid4().hex}_program.py"
    program_path.write_text(render_program_state_module(module), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"htp_stage_{uuid4().hex}", program_path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_checked_in_variants_align_with_rendered_stage_modules(tmp_path: Path) -> None:
    variants = (
        surface_program.PROGRAM_MODULE,
        core_ir.PROGRAM_MODULE,
        scheduled_ir.PROGRAM_MODULE,
        backend_ready_ir.PROGRAM_MODULE,
    )

    for variant in variants:
        loaded = _import_rendered_module(tmp_path, variant)
        rebuilt = loaded.program_module()

        assert rebuilt.to_program_dict() == variant.to_program_dict()
        assert rebuilt.run(mode="sim")["ok"] is True
