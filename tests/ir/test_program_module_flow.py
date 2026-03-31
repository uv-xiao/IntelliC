from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
from uuid import uuid4

from htp.ir.aspects import EffectsAspect, LayoutAspect, ScheduleAspect, TypesAspect
from htp.ir.identity_state import BindingTable, EntityTable, RewriteMap
from htp.ir.interpreter import register_interpreter
from htp.ir.module import (
    ProgramAspects,
    ProgramEntrypoint,
    ProgramIdentity,
    ProgramItems,
    ProgramModule,
)
from htp.ir.render import render_program_module_payload


def test_program_module_definition_execution_and_transformation(tmp_path: Path) -> None:
    interpreter_id = f"htp.test.flow.{uuid4().hex}"
    register_interpreter(interpreter_id, _demo_runner)

    module = _demo_module(interpreter_id=interpreter_id, kernel_entry="vector_add", pipeline_depth=1)

    execution = module.run(1, 2, scale=4, trace={"mode": "capture"})
    assert execution == {
        "entry": "run",
        "kernel_entry": "vector_add",
        "pipeline_depth": 1,
        "args": [1, 2],
        "kwargs": {"scale": 4},
        "mode": "sim",
        "trace": {"mode": "capture"},
    }

    transformed = _rewrite_module(
        module,
        kernel_entry="vector_add_tiled",
        pipeline_depth=3,
        added_analysis={"tile": [32, 32], "pipeline_depth": 3},
    )
    assert transformed.items.kernel_ir.entry == "vector_add_tiled"
    assert isinstance(transformed.aspects.types, TypesAspect)
    assert isinstance(transformed.aspects.layout, LayoutAspect)
    assert isinstance(transformed.aspects.effects, EffectsAspect)
    assert isinstance(transformed.aspects.schedule, ScheduleAspect)
    assert isinstance(transformed.identity.entities, EntityTable)
    assert isinstance(transformed.identity.bindings, BindingTable)
    assert transformed.aspects.schedule["pipeline_depth"] == 3
    assert transformed.analyses["transform.demo"]["pipeline_depth"] == 3

    round_tripped = _import_rendered_module(tmp_path, transformed)
    assert round_tripped.to_payload() == transformed.to_payload()
    assert round_tripped.run(scale=2) == {
        "entry": "run",
        "kernel_entry": "vector_add_tiled",
        "pipeline_depth": 3,
        "args": [],
        "kwargs": {"scale": 2},
        "mode": "sim",
        "trace": None,
    }


def test_program_module_aspects_round_trip_typed_wrappers() -> None:
    module = ProgramModule.from_program_dict(
        {
            "entry": "run",
            "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": "run"}},
            "kernel_ir": {},
            "workload_ir": {},
            "types": {
                "schema": "htp.types.v1",
                "values": {"acc": {"dtype": "f32"}},
                "buffers": {},
                "aliases": {"acc": "tmp0"},
            },
            "layout": {
                "schema": "htp.layout.v1",
                "memory_spaces": {"acc": "register"},
                "threading": {},
                "tiling": {},
                "launch": {"num_warps": 4},
            },
            "effects": {
                "schema": "htp.effects.v1",
                "reads": {"op0": ["acc"]},
                "writes": {},
                "barriers": [],
                "channels": [],
                "protocols": [{"name": "token_fifo"}],
            },
            "schedule": {
                "schema": "htp.schedule.v1",
                "ticks": [],
                "ordered_ops": ["op0"],
                "pipeline_depth": 2,
                "legality": {"ok": True, "reasons": []},
            },
        }
    )

    assert isinstance(module.aspects.types, TypesAspect)
    assert isinstance(module.aspects.layout, LayoutAspect)
    assert isinstance(module.aspects.effects, EffectsAspect)
    assert isinstance(module.aspects.schedule, ScheduleAspect)
    assert module.aspects.types["aliases"] == {"acc": "tmp0"}
    assert module.aspects.layout["launch"] == {"num_warps": 4}
    assert module.aspects.effects["protocols"] == [{"name": "token_fifo"}]
    assert module.aspects.schedule["legality"] == {"ok": True, "reasons": []}
    assert module.to_state_dict()["schedule"]["legality"] == {"ok": True, "reasons": []}


def test_program_module_identity_round_trip_typed_wrappers() -> None:
    module = ProgramModule.from_program_dict(
        {
            "entry": "run",
            "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": "run"}},
            "kernel_ir": {},
            "workload_ir": {},
            "entities_payload": {
                "schema": "htp.ids.entities.v1",
                "def_id": "run",
                "entities": [{"entity_id": "E0", "name": "vector_add"}],
                "node_to_entity": [{"node_id": "N0", "entity_id": "E0"}],
            },
            "bindings_payload": {
                "schema": "htp.ids.bindings.v1",
                "def_id": "run",
                "scopes": [{"scope_id": "S0"}],
                "bindings": [{"binding_id": "B0", "name": "acc"}],
                "name_uses": [{"scope_id": "S0", "name": "acc", "binding_id": "B0"}],
            },
            "entity_map_payload": {
                "schema": "htp.entity_map.v1",
                "entities": [{"before": "E0", "after": ["E1"], "reason": "rewrite"}],
                "pass_id": "demo.pass",
                "stage_before": "s00",
                "stage_after": "s01",
            },
            "binding_map_payload": {
                "schema": "htp.binding_map.v1",
                "bindings": [{"before": "B0", "after": ["B1"], "reason": "rewrite"}],
                "pass_id": "demo.pass",
                "stage_before": "s00",
                "stage_after": "s01",
            },
        }
    )

    assert isinstance(module.identity.entities, EntityTable)
    assert isinstance(module.identity.bindings, BindingTable)
    assert isinstance(module.identity.entity_map, RewriteMap)
    assert isinstance(module.identity.binding_map, RewriteMap)
    assert module.identity.entities["entities"][0]["entity_id"] == "E0"
    assert module.identity.binding_map["stage_after"] == "s01"
    assert module.to_state_dict()["entity_map_payload"]["entities"][0]["after"] == ["E1"]


def _demo_module(*, interpreter_id: str, kernel_entry: str, pipeline_depth: int) -> ProgramModule:
    return ProgramModule(
        items=ProgramItems(
            canonical_ast={
                "schema": "htp.program_ast.v1",
                "program": {
                    "entry": "run",
                    "items": [
                        {
                            "kind": "Kernel",
                            "name": kernel_entry,
                            "body": [
                                "acc = A + B",
                                "store(C, acc)",
                            ],
                        }
                    ],
                },
            },
            kernel_ir={
                "schema": "htp.kernel_ir.v1",
                "entry": kernel_entry,
                "args": [
                    {"name": "A", "kind": "buffer", "dtype": "f32"},
                    {"name": "B", "kind": "buffer", "dtype": "f32"},
                    {"name": "C", "kind": "buffer", "dtype": "f32"},
                ],
                "ops": [
                    {
                        "op_id": "op0",
                        "op": "add",
                        "inputs": ["A", "B"],
                        "outputs": ["acc"],
                    },
                    {
                        "op_id": "op1",
                        "op": "store",
                        "inputs": ["acc"],
                        "outputs": ["C"],
                    },
                ],
            },
            workload_ir={
                "schema": "htp.workload_ir.v1",
                "entry": "run",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": kernel_entry,
                        "args": ["A", "B", "C"],
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
        ),
        aspects=ProgramAspects(
            types={
                "schema": "htp.types.v1",
                "values": {
                    "A": {"dtype": "f32"},
                    "B": {"dtype": "f32"},
                    "C": {"dtype": "f32"},
                    "acc": {"dtype": "f32"},
                },
                "buffers": {},
            },
            layout={
                "schema": "htp.layout.v1",
                "memory_spaces": {"A": "global", "B": "global", "C": "global"},
                "threading": {},
                "tiling": {},
            },
            effects={
                "schema": "htp.effects.v1",
                "reads": {"op0": ["A", "B"]},
                "writes": {"op1": ["C"]},
                "barriers": [],
                "channels": [],
            },
            schedule={
                "schema": "htp.schedule.v1",
                "ticks": [{"tick": 0, "op_id": "op0"}, {"tick": 1, "op_id": "op1"}],
                "ordered_ops": ["op0", "op1"],
                "pipeline_depth": pipeline_depth,
            },
        ),
        analyses={
            "semantic.demo": {
                "schema": "htp.analysis.semantic_demo.v1",
                "kernel_entry": kernel_entry,
                "op_count": 2,
            }
        },
        identity=ProgramIdentity(
            entities={
                "schema": "htp.ids.entities.v1",
                "entities": [{"entity_id": "E0", "name": kernel_entry}],
            },
            bindings={"schema": "htp.ids.bindings.v1", "bindings": [{"binding_id": "B0", "name": "acc"}]},
        ),
        entrypoints=(ProgramEntrypoint(name="run", interpreter_id=interpreter_id),),
        meta={"source": "test", "program_extras": {"target": {"backend": "cpu_ref", "option": "sim"}}},
    )


def _rewrite_module(
    module: ProgramModule,
    *,
    kernel_entry: str,
    pipeline_depth: int,
    added_analysis: dict[str, Any],
) -> ProgramModule:
    payload = module.to_state_dict()
    payload["kernel_ir"] = {
        **payload["kernel_ir"],
        "entry": kernel_entry,
    }
    payload["workload_ir"] = {
        **payload["workload_ir"],
        "tasks": [
            {
                **task,
                "kernel": kernel_entry,
            }
            for task in payload["workload_ir"]["tasks"]
        ],
    }
    payload["schedule"] = {
        **payload["schedule"],
        "pipeline_depth": pipeline_depth,
    }
    payload["analysis"] = {
        **payload["analysis"],
        "transform.demo": {
            "schema": "htp.analysis.transform_demo.v1",
            "kernel_entry": kernel_entry,
            **added_analysis,
        },
    }
    payload["canonical_ast"] = {
        **payload["canonical_ast"],
        "program": {
            **payload["canonical_ast"]["program"],
            "items": [
                {
                    "kind": "Kernel",
                    "name": kernel_entry,
                    "body": [
                        "for tile in tiles(A, B):",
                        "    acc = fused_add(tile)",
                        "store(C, acc)",
                    ],
                }
            ],
        },
    }
    return ProgramModule.from_program_dict(payload)


def _import_rendered_module(tmp_path: Path, module: ProgramModule) -> ProgramModule:
    program_path = tmp_path / "program.py"
    program_path.write_text(render_program_module_payload(module.to_payload()), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"htp_test_program_{uuid4().hex}", program_path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded.program_module()


def _demo_runner(
    module: ProgramModule,
    *,
    entry: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    mode: str,
    runtime: Any | None,
    trace: Any | None,
) -> dict[str, Any]:
    del runtime
    return {
        "entry": entry,
        "kernel_entry": module.items.kernel_ir.entry,
        "pipeline_depth": module.aspects.schedule["pipeline_depth"],
        "args": list(args),
        "kwargs": dict(kwargs),
        "mode": mode,
        "trace": trace,
    }
