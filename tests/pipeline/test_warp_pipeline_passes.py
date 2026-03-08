from __future__ import annotations

import json

from htp.pipeline.defaults import MANDATORY_PASS_IDS, run_default_pipeline
from htp.wsp import program as wsp_program
from htp.wsp import schedule as wsp_schedule
from htp.wsp import workload as wsp_workload


def _wsp_program() -> dict[str, object]:
    return wsp_program(
        entry="gemm_tile",
        target={"backend": "nvgpu", "option": "ampere"},
        kernel={
            "name": "gemm_tile",
            "args": [
                {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
                {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
                {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
                {"name": "M", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
                {"name": "N", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
                {"name": "K", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
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
        workload=wsp_workload(
            entry="gemm_tile",
            tasks=[
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "gemm_tile",
                    "args": ["A", "B", "C", "M", "N", "K"],
                }
            ],
        ),
        schedule=wsp_schedule(
            bind={"grid": "block", "lane": "warp"},
            pipeline={"depth": 3, "buffering": "double"},
            resources={"num_warps": 4},
            specialize={"operator": "matmul"},
        ),
    )


def test_default_pipeline_emits_warp_and_pipeline_analyses(tmp_path):
    package_dir = tmp_path / "out"

    result = run_default_pipeline(package_dir=package_dir, program=_wsp_program())
    manifest = json.loads((package_dir / "manifest.json").read_text())
    stage_graph = manifest["stages"]["graph"]

    assert "htp::analyze_warp_specialization@1" in MANDATORY_PASS_IDS
    assert "htp::apply_warp_specialization@1" in MANDATORY_PASS_IDS
    assert "htp::analyze_software_pipeline@1" in MANDATORY_PASS_IDS
    assert "htp::apply_software_pipeline@1" in MANDATORY_PASS_IDS
    assert manifest["stages"]["current"] == result.current_stage

    warp_stage = next(stage for stage in stage_graph if stage["pass"] == "htp::analyze_warp_specialization@1")
    pipeline_stage = next(
        stage for stage in stage_graph if stage["pass"] == "htp::analyze_software_pipeline@1"
    )
    warp_plan = json.loads(
        (package_dir / "ir" / "stages" / warp_stage["id"] / "analysis" / "warp_role_plan.json").read_text()
    )
    pipeline_plan = json.loads(
        (package_dir / "ir" / "stages" / pipeline_stage["id"] / "analysis" / "pipeline_plan.json").read_text()
    )

    assert warp_plan["roles"] == [
        {"name": "producer", "count": 2, "responsibilities": ["async_copy", "handoff"]},
        {"name": "consumer", "count": 2, "responsibilities": ["mma", "accumulate"]},
    ]
    assert warp_plan["subgroup_kind"] == "warp"
    assert pipeline_plan["buffering"] == "double"
    assert pipeline_plan["stages"] == ["prefetch", "compute", "drain"]
    assert pipeline_plan["steady_state_slots"] == [0, 1]

    assert result.program["schedule"]["specialization"] == {
        "applied": True,
        "kind": "warp",
        "roles": warp_plan["roles"],
        "handoff": warp_plan["handoffs"][0],
    }
    assert result.program["schedule"]["software_pipeline"] == {
        "applied": True,
        "depth": 3,
        "buffering": "double",
        "steady_state_slots": [0, 1],
        "stage_order": ["prefetch", "compute", "drain"],
    }
    assert result.program["scheduled_ops"][0]["slot"] == 0
    assert result.program["scheduled_ops"][0]["pipeline_stage"] == "compute"


def test_default_pipeline_falls_back_to_single_role_without_wsp_directives(tmp_path):
    package_dir = tmp_path / "out"

    result = run_default_pipeline(
        package_dir=package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["load", "mma", "store"],
            "analysis": {},
            "package": {"emitted": False},
            "target": {"backend": "nvgpu", "option": "ampere"},
        },
    )

    assert result.program["schedule"]["specialization"]["kind"] == "single_role"
    assert result.program["schedule"]["software_pipeline"]["depth"] == 1
