from __future__ import annotations

from htp.ir.program.module import ProgramModule
from htp.passes.replay_program import render_program_state_module


def test_render_program_state_module_builds_program_module_surface():
    program = _demo_program()
    text = render_program_state_module(program)

    assert (
        "from htp.ir.program.module import ProgramAspects, ProgramEntrypoint, ProgramIdentity, ProgramItems, ProgramModule"
        in text
    )
    assert "PROGRAM_MODULE = ProgramModule(" in text
    assert "def program_state():" in text
    assert "def program_module():" in text
    assert "return PROGRAM_MODULE.run(" in text


def test_program_module_snapshot_interpreter_keeps_program_dict_shape():
    program = _demo_program()

    module = ProgramModule.from_program_dict(program)

    assert module.run() == module.to_program_dict()


def _demo_program() -> dict[str, object]:
    return {
        "entry": "vector_add",
        "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": "vector_add"}},
        "kernel_ir": {
            "schema": "htp.kernel_ir.v1",
            "entry": "vector_add",
            "args": [],
            "buffers": [],
            "ops": [],
        },
        "workload_ir": {
            "schema": "htp.workload_ir.v1",
            "entry": "vector_add",
            "tasks": [],
            "channels": [],
            "dependencies": [],
        },
        "types": {"schema": "htp.types.v1", "values": {}, "buffers": {}},
        "layout": {"schema": "htp.layout.v1", "memory_spaces": {}, "threading": {}, "tiling": {}},
        "effects": {
            "schema": "htp.effects.v1",
            "reads": {},
            "writes": {},
            "barriers": [],
            "channels": [],
        },
        "schedule": {"schema": "htp.schedule.v1", "ticks": [], "ordered_ops": [], "pipeline_depth": 0},
        "analysis": {"schedule": {"schema": "htp.analysis.schedule_plan.v1", "ticks": []}},
        "entities_payload": {
            "schema": "htp.ids.entities.v1",
            "def_id": "demo",
            "entities": [],
            "node_to_entity": [],
        },
        "bindings_payload": {
            "schema": "htp.ids.bindings.v1",
            "def_id": "demo",
            "scopes": [],
            "bindings": [],
            "name_uses": [],
        },
    }
