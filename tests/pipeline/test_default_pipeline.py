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
    assert result.current_stage == "s06"

    manifest = json.loads((package_dir / "manifest.json").read_text())
    stage_graph = manifest["stages"]["graph"]

    assert manifest["stages"]["current"] == "s06"
    assert [stage["pass"] for stage in stage_graph] == [None, *MANDATORY_PASS_IDS]
    assert len(stage_graph) == len(MANDATORY_PASS_IDS) + 1

    for stage in stage_graph:
        assert (package_dir / stage["dir"]).exists()
        assert (package_dir / stage["summary"]).exists()
        assert (package_dir / stage["analysis_index"]).exists()
        assert (package_dir / stage["program_pyast"]).exists()
        for relpath in stage["semantic"].values():
            assert (package_dir / relpath).exists(), relpath

    trace_lines = (package_dir / "ir" / "pass_trace.jsonl").read_text().strip().splitlines()
    trace_events = [json.loads(line) for line in trace_lines]
    assert [event["pass_id"] for event in trace_events] == list(MANDATORY_PASS_IDS)

    semantic_stage = next(stage for stage in stage_graph if stage["pass"] == "htp::semantic_model@1")
    semantic_kernel_ir = json.loads((package_dir / semantic_stage["semantic"]["kernel_ir"]).read_text())
    semantic_workload_ir = json.loads((package_dir / semantic_stage["semantic"]["workload_ir"]).read_text())
    assert semantic_kernel_ir["entry"] == "gemm_tile"
    assert semantic_kernel_ir["ops"] == [
        {
            "op_id": "op0",
            "entity_id": "gemm_tile:E6",
            "op": "matmul",
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
    analysis_index = json.loads((package_dir / analyze_stage["analysis_index"]).read_text())
    assert analysis_index == {
        "schema": "htp.analysis.index.v1",
        "analyses": [
            {
                "analysis_id": "htp::SchedulePlan@1",
                "schema": "htp.analysis.schedule_plan.v1",
                "path": "ir/stages/s04/analysis/schedule_plan.json",
            }
        ],
    }

    schedule_plan = json.loads(
        (package_dir / "ir" / "stages" / "s04" / "analysis" / "schedule_plan.json").read_text()
    )
    assert schedule_plan == {
        "schema": "htp.analysis.schedule_plan.v1",
        "entry": "gemm_tile",
        "target": {"backend": "nvgpu", "option": "ampere"},
        "pipeline_depth": 1,
        "ticks": [
            {
                "tick": 0,
                "op_id": "op0",
                "op": "matmul",
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
    assert result.program["types"]["buffers"]["A"] == "f32[MxK]"
    assert result.program["layout"]["memory_spaces"]["C"] == "global"
    assert result.program["effects"]["reads"] == {"op0": ["A", "B"]}
    assert result.program["analysis"]["schedule"]["ticks"] == schedule_plan["ticks"]
    assert result.program["schedule"]["ordered_ops"] == ["op0"]
    assert result.program["scheduled_ops"][0]["op"] == "matmul"
    assert result.program["package"]["emitted"] is True
    assert result.program["package"]["scheduled_tick_count"] == 1
    assert result.program["package"]["kernel_entry"] == "gemm_tile"
    replay = bind(package_dir).load(mode="sim").replay("s06")
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["entry"] == "gemm_tile"
