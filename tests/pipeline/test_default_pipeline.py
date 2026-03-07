import json

from htp.pipeline.defaults import MANDATORY_PASS_IDS, run_default_pipeline


def test_default_pipeline_runs_all_mandatory_passes(tmp_path):
    package_dir = tmp_path / "out"

    result = run_default_pipeline(package_dir=package_dir)

    assert result.pass_ids == list(MANDATORY_PASS_IDS)
    assert result.current_stage == "s05"

    manifest = json.loads((package_dir / "manifest.json").read_text())
    stage_graph = manifest["stages"]["graph"]

    assert manifest["stages"]["current"] == "s05"
    assert [stage["pass"] for stage in stage_graph] == [None, *MANDATORY_PASS_IDS]
    assert len(stage_graph) == len(MANDATORY_PASS_IDS) + 1

    for stage in stage_graph:
        assert (package_dir / stage["dir"]).exists()
        assert (package_dir / stage["summary"]).exists()
        assert (package_dir / stage["analysis_index"]).exists()

    trace_lines = (package_dir / "ir" / "pass_trace.jsonl").read_text().strip().splitlines()
    trace_events = [json.loads(line) for line in trace_lines]
    assert [event["pass_id"] for event in trace_events] == list(MANDATORY_PASS_IDS)

    analyze_stage = next(stage for stage in stage_graph if stage["pass"] == "htp::analyze_schedule@1")
    analysis_index = json.loads((package_dir / analyze_stage["analysis_index"]).read_text())
    assert analysis_index == {
        "schema": "htp.analysis.index.v1",
        "analyses": [
            {
                "analysis_id": "htp::SchedulePlan@1",
                "schema": "htp.analysis.schedule_plan.v1",
                "path": "ir/stages/s03/analysis/schedule_plan.json",
            }
        ],
    }

    schedule_plan = json.loads(
        (package_dir / "ir" / "stages" / "s03" / "analysis" / "schedule_plan.json").read_text()
    )
    assert schedule_plan == {
        "schema": "htp.analysis.schedule_plan.v1",
        "entry": "demo_kernel",
        "ticks": [
            {"tick": 0, "op": "load_tile"},
            {"tick": 1, "op": "compute_tile"},
            {"tick": 2, "op": "store_tile"},
        ],
    }

    assert result.program["analysis"]["schedule"]["ticks"] == schedule_plan["ticks"]
    assert result.program["package"]["emitted"] is True
