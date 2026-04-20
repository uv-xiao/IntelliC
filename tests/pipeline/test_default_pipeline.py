import json

from htp.bindings.api import bind
from htp.pipeline.defaults import MANDATORY_PASS_IDS, run_default_pipeline


def _gemm_program() -> dict[str, object]:
    return {
        "entry": "gemm_tile",
        "kernel": {
            "name": "gemm_tile",
            "args": [
                {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
                {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
                {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
                {"name": "M", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "N", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "K", "kind": "scalar", "dtype": "i32", "role": "shape"},
            ],
            "ops": [
                {
                    "op": "matmul",
                    "lhs": "A",
                    "rhs": "B",
                    "out": "C",
                    "m": "M",
                    "n": "N",
                    "k": "K",
                    "dtype": "f32",
                }
            ],
        },
        "workload": {
            "entry": "gemm_tile",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "gemm_tile",
                    "args": ["A", "B", "C", "M", "N", "K"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "analysis": {},
        "package": {"emitted": False},
        "target": {"backend": "nvgpu", "option": "ampere"},
    }


def test_default_pipeline_runs_all_mandatory_passes(tmp_path):
    package_dir = tmp_path / "out"

    result = run_default_pipeline(package_dir=package_dir, program=_gemm_program())

    assert result.pass_ids == list(MANDATORY_PASS_IDS)
    assert result.current_stage == f"s{len(MANDATORY_PASS_IDS):02d}"

    manifest = json.loads((package_dir / "manifest.json").read_text())
    stage_graph = manifest["stages"]["graph"]

    assert manifest["stages"]["current"] == result.current_stage
    assert [stage["pass"] for stage in stage_graph] == [None, *MANDATORY_PASS_IDS]
    assert len(stage_graph) == len(MANDATORY_PASS_IDS) + 1

    for stage in stage_graph:
        assert (package_dir / stage["dir"]).exists()
        assert (package_dir / stage["program"]).exists()
        assert (package_dir / stage["stage"]).exists()
        assert (package_dir / stage["state"]).exists()

    current_stage = next(stage for stage in stage_graph if stage["id"] == result.current_stage)
    program_text = (package_dir / current_stage["runnable_py"]["program_py"]).read_text()
    assert '"""Readable staged Python snapshot for HTP replay and debugging."""' in program_text
    assert "ITEMS_PAYLOAD = {" in program_text
    assert "_ITEMS = ProgramItems(**ITEMS_PAYLOAD)" in program_text
    assert "PROGRAM_MODULE = ProgramModule(" in program_text
    assert "def program_module():" in program_text
    assert "def program_state():" in program_text
    assert "return PROGRAM_MODULE.run(" in program_text

    state_payload = json.loads((package_dir / current_stage["state"]).read_text())
    assert state_payload["schema"] == "htp.program_module.v1"
    assert state_payload["items"]["kernel_ir"]["entry"] == "gemm_tile"
    stage_summary = json.loads((package_dir / current_stage["stage"]).read_text())
    assert stage_summary["schema"] == "htp.stage.v2"
    assert stage_summary["paths"]["program"] == current_stage["program"]
    assert stage_summary["paths"]["state"] == current_stage["state"]

    trace_lines = (package_dir / "ir" / "pass_trace.jsonl").read_text().strip().splitlines()
    trace_events = [json.loads(line) for line in trace_lines]
    assert [event["pass_id"] for event in trace_events] == list(MANDATORY_PASS_IDS)
    analyze_trace = next(event for event in trace_events if event["pass_id"] == "htp::analyze_schedule@1")
    assert analyze_trace["requires_satisfied"] == {
        "requires": {
            "Type.LayoutChecked@1": True,
            "Type.EffectsChecked@1": True,
        },
        "analysis_requires": {
            "Analysis.LoopDeps@1": True,
            "Analysis.AsyncResourceChecks@1": True,
        },
        "layout_invariants": {
            "Layout.Typed@1": True,
        },
        "effect_invariants": {
            "Effects.ProtocolBalanced@1": True,
            "Effects.Typed@1": True,
        },
    }
    assert analyze_trace["cap_delta"]["preserved_layout_invariants"] == ["Layout.Typed@1"]
    assert analyze_trace["cap_delta"]["preserved_effect_invariants"] == [
        "Effects.ProtocolBalanced@1",
        "Effects.Typed@1",
    ]
    semantic_trace = next(event for event in trace_events if event["pass_id"] == "htp::semantic_model@1")
    assert semantic_trace["cap_delta"]["provides"] == ["Semantic.ModelBuilt@1"]
    assert semantic_trace["cap_delta"]["added_analyses"] == ["Semantic.ModelBuilt@1"]

    semantic_stage = next(stage for stage in stage_graph if stage["pass"] == "htp::semantic_model@1")
    semantic_state = json.loads((package_dir / semantic_stage["state"]).read_text())
    semantic_kernel_ir = semantic_state["items"]["kernel_ir"]
    semantic_workload_ir = semantic_state["items"]["workload_ir"]
    assert semantic_kernel_ir["entry"] == "gemm_tile"
    assert semantic_kernel_ir["ops"] == [
        {
            "op_id": "op0",
            "entity_id": "gemm_tile:E6",
            "op": "matmul",
            "intrinsic": "portable.matmul",
            "inputs": ["A", "B"],
            "outputs": ["C"],
            "attrs": {"dtype": "f32", "m": "M", "n": "N", "k": "K"},
            "effects": {"reads": ["A", "B"], "writes": ["C"]},
        }
    ]
    assert semantic_workload_ir["tasks"] == [
        {
            "task_id": "task0",
            "kind": "kernel_call",
            "kernel": "gemm_tile",
            "args": ["A", "B", "C", "M", "N", "K"],
            "entity_id": "gemm_tile:E7",
        }
    ]

    analyze_stage = next(stage for stage in stage_graph if stage["pass"] == "htp::analyze_schedule@1")
    analysis_index = json.loads((package_dir / analyze_stage["stage"]).read_text())["analysis_inventory"]
    assert analysis_index == [
        {
            "analysis_id": "htp::SchedulePlan@1",
            "schema": "htp.analysis.schedule_plan.v1",
            "path": f"ir/stages/{analyze_stage['id']}/analysis/schedule_plan.json",
        }
    ]
    loop_dep_stage = next(
        stage for stage in stage_graph if stage["pass"] == "htp::analyze_loop_dependencies@1"
    )
    loop_deps = json.loads((package_dir / loop_dep_stage["dir"] / "analysis" / "loop_deps.json").read_text())
    assert loop_deps == {
        "schema": "htp.analysis.loop_deps.v1",
        "entry": "gemm_tile",
        "op_ids": ["op0"],
        "edges": [],
    }
    async_stage = next(stage for stage in stage_graph if stage["pass"] == "htp::analyze_async_resources@1")
    async_checks = json.loads(
        (package_dir / async_stage["dir"] / "analysis" / "async_resources.json").read_text()
    )
    assert async_checks == {
        "schema": "htp.analysis.async_resources.v1",
        "entry": "gemm_tile",
        "tokens": [],
        "barriers": [],
        "channel_protocols": [],
        "collectives": [],
        "unresolved_tokens": [],
        "pending_collectives": [],
        "barrier_scopes": [],
        "resource_summary": {
            "token_count": 0,
            "barrier_count": 0,
            "collective_count": 0,
            "pending_token_count": 0,
            "pending_collective_count": 0,
            "protocol_hazard_count": 0,
            "op_count": 1,
        },
    }

    schedule_plan = json.loads(
        (package_dir / analyze_stage["dir"] / "analysis" / "schedule_plan.json").read_text()
    )
    assert schedule_plan == {
        "schema": "htp.analysis.schedule_plan.v1",
        "entry": "gemm_tile",
        "target": {"backend": "nvgpu", "option": "ampere"},
        "pipeline_depth": 1,
        "directives": {
            "tile": {},
            "bind": {},
            "pipeline": {},
            "resources": {},
            "specialize": {},
        },
        "buffering_strategy": "single",
        "launch": {"grid": "grid", "lane": "thread", "num_warps": 1},
        "warp_role_plan": {"kind": "single_role", "roles": ["compute"]},
        "legality": {"ok": True, "reasons": []},
        "ticks": [
            {
                "tick": 0,
                "op_id": "op0",
                "op": "matmul",
                "intrinsic": "portable.matmul",
                "phase": "compute",
                "reads": ["A", "B"],
                "writes": ["C"],
                "latency": 2,
            },
        ],
    }

    assert result.program["canonical_ast"]["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert result.program["kernel_ir"]["entry"] == "gemm_tile"
    assert result.program["workload_ir"]["entry"] == "gemm_tile"
    assert result.program["types"]["buffers"]["A"] == {
        "kind": "buffer",
        "dtype": {"kind": "scalar", "name": "f32"},
        "shape": {
            "kind": "shape",
            "dims": [
                {"kind": "symbol", "symbol": "M"},
                {"kind": "symbol", "symbol": "K"},
            ],
        },
        "space": "global",
        "alias_of": None,
    }
    assert result.program["layout"]["memory_spaces"]["C"] == "global"
    assert result.program["effects"]["reads"] == {"op0": ["A", "B"]}
    assert result.program["analysis"]["loop_deps"]["edges"] == []
    assert result.program["analysis"]["async_resources"]["resource_summary"]["op_count"] == 1
    assert result.program["analysis"]["schedule"]["ticks"] == schedule_plan["ticks"]
    assert result.program["schedule"]["ordered_ops"] == ["op0"]
    assert result.program["schedule"]["legality"] == {"ok": True, "reasons": []}
    assert result.program["scheduled_ops"][0]["op"] == "matmul"
    assert result.program["package"]["emitted"] is True
    assert result.program["package"]["scheduled_tick_count"] == 1
    assert result.program["package"]["kernel_entry"] == "gemm_tile"
    replay = bind(package_dir).load(mode="sim").replay(result.current_stage)
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["entry"] == "gemm_tile"
