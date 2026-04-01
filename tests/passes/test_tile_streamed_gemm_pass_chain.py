from __future__ import annotations

from dataclasses import replace

from htp.ir.core.nodes import Kernel, ProcessGraph, TaskGraph
from htp.ir.interpreters.entrypoints import NODE_PROGRAM_INTERPRETER_ID
from htp.ir.program.build import build_tile_streamed_gemm_core_module
from htp.ir.program.module import ProgramEntrypoint
from htp.passes.backend_ready import backend_ready_rewrite
from htp.passes.enrich_protocol import enrich_schedule_and_protocol
from htp.passes.surface_to_core import surface_to_core_normalize
from htp.passes.tile_and_stage import tile_and_stage_rewrite


def tile_streamed_gemm_surface_module():
    return replace(
        build_tile_streamed_gemm_core_module(),
        entrypoints=(ProgramEntrypoint(name="run", interpreter_id=NODE_PROGRAM_INTERPRETER_ID),),
        meta={"variant": "surface"},
    )


def build_tile_streamed_gemm_scheduled_module():
    return enrich_schedule_and_protocol(tile_and_stage_rewrite(build_tile_streamed_gemm_core_module()))


def test_surface_to_core_normalization_emits_core_program_module() -> None:
    surface_module = tile_streamed_gemm_surface_module()
    normalized = surface_to_core_normalize(surface_module)

    assert normalized.meta["variant"] == "core"
    assert isinstance(normalized.items.typed_items[0], Kernel)
    assert isinstance(normalized.items.typed_items[1], TaskGraph)
    assert isinstance(normalized.items.typed_items[2], ProcessGraph)


def test_tile_and_stage_rewrite_emits_scheduled_variant() -> None:
    core = build_tile_streamed_gemm_core_module()
    scheduled = tile_and_stage_rewrite(core)

    assert scheduled.meta["variant"] == "scheduled"
    assert scheduled.aspects.schedule["pipeline_depth"] == 2
    assert scheduled.items.typed_items[2].processes[0].steps[0].kind == "put"


def test_schedule_protocol_enrichment_adds_protocol_facts() -> None:
    core = build_tile_streamed_gemm_core_module()
    enriched = enrich_schedule_and_protocol(tile_and_stage_rewrite(core))

    assert enriched.aspects.effects["protocols"][0]["channel"] == "tile_stream"
    assert enriched.aspects.schedule["protocol_roles"][0]["task"] == "load_tiles"


def test_backend_ready_rewrite_preserves_program_module_executability() -> None:
    scheduled = build_tile_streamed_gemm_scheduled_module()
    backend_ready = backend_ready_rewrite(scheduled)

    assert backend_ready.meta["variant"] == "backend_ready"
    assert backend_ready.run(mode="sim")["ok"] is True
