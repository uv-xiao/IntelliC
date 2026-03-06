import json

import pytest

from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.passes.contracts import AnalysisOutput, PassContract
from htp.passes.manager import PassManager, PassResult


def test_pass_trace_emits_normalized_event(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    initial_stage = write_stage(
        package_dir,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        ),
    )
    manager = PassManager(package_dir=package_dir, stages=[initial_stage], current_stage="s00")
    contract = PassContract.analysis(
        pass_id="pkg::warp_role_plan@1",
        owner="pkg",
        requires=("Dialect.WSPEnabled",),
        provides=("Analysis.WarpRolePlan@1",),
        analysis_produces=(
            AnalysisOutput(
                analysis_id="pkg::WarpRolePlan@1",
                schema="htp.analysis.warp_role_plan.v1",
                path_hint="analysis/warp_role_plan.json",
            ),
        ),
        outputs=("analysis.index", "analysis.result"),
    )

    stage_record = manager.run(
        contract,
        lambda stage_before: PassResult(
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
            analyses={
                "analysis/warp_role_plan.json": {
                    "schema": "htp.analysis.warp_role_plan.v1",
                    "roles": [],
                }
            },
            diagnostics=(),
            time_ms=3.5,
        ),
    )

    assert stage_record["id"] == "s01"
    assert manager.current_stage == "s01"
    assert manager.stages == [initial_stage, stage_record]
    assert (package_dir / "ir/stages/s00").exists()
    assert (package_dir / "ir/stages/s01").exists()

    trace_path = package_dir / "ir" / "pass_trace.jsonl"
    lines = trace_path.read_text().strip().splitlines()
    assert len(lines) == 1

    assert json.loads(lines[0]) == {
        "schema": "htp.pass_trace_event.v1",
        "pass_id": "pkg::warp_role_plan@1",
        "kind": "analysis",
        "ast_effect": "preserves",
        "stage_before": "s00",
        "stage_after": "s01",
        "time_ms": 3.5,
        "requires": ["Dialect.WSPEnabled"],
        "requires_satisfied": {},
        "cap_delta": {
            "provides": ["Analysis.WarpRolePlan@1"],
            "invalidates": [],
        },
        "analysis": {
            "requires": [],
            "produces": [
                {
                    "analysis_id": "pkg::WarpRolePlan@1",
                    "schema": "htp.analysis.warp_role_plan.v1",
                    "path": "ir/stages/s01/analysis/warp_role_plan.json",
                }
            ],
        },
        "runnable_py": {
            "status": "preserves",
            "modes": ["sim"],
            "program_py": "ir/stages/s01/program.py",
        },
        "dumps": {
            "program_py": "ir/stages/s01/program.py",
            "program_pyast": None,
            "metadata": {},
            "ids": {
                "entities": "ir/stages/s01/ids/entities.json",
                "bindings": "ir/stages/s01/ids/bindings.json",
            },
            "analysis_index": "ir/stages/s01/analysis/index.json",
            "stubs": None,
        },
        "maps": {},
        "diagnostics": [],
    }


def test_pass_manager_requires_declared_analysis_result(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    initial_stage = write_stage(
        package_dir,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        ),
    )
    manager = PassManager(package_dir=package_dir, stages=[initial_stage], current_stage="s00")
    contract = PassContract.analysis(
        pass_id="pkg::warp_role_plan@1",
        owner="pkg",
        analysis_produces=(
            AnalysisOutput(
                analysis_id="pkg::WarpRolePlan@1",
                schema="htp.analysis.warp_role_plan.v1",
                path_hint="analysis/warp_role_plan.json",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Missing analysis result"):
        manager.run(
            contract,
            lambda stage_before: PassResult(
                runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
                analyses={},
            ),
        )


def test_pass_manager_rejects_undeclared_analysis_result(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    initial_stage = write_stage(
        package_dir,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        ),
    )
    manager = PassManager(package_dir=package_dir, stages=[initial_stage], current_stage="s00")
    contract = PassContract.analysis(
        pass_id="pkg::warp_role_plan@1",
        owner="pkg",
        analysis_produces=(
            AnalysisOutput(
                analysis_id="pkg::WarpRolePlan@1",
                schema="htp.analysis.warp_role_plan.v1",
                path_hint="analysis/warp_role_plan.json",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Undeclared analysis result"):
        manager.run(
            contract,
            lambda stage_before: PassResult(
                runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
                analyses={
                    "analysis/warp_role_plan.json": {"schema": "htp.analysis.warp_role_plan.v1"},
                    "analysis/extra.json": {"schema": "htp.analysis.extra.v1"},
                },
            ),
        )


def test_pass_manager_requires_runnable_py_to_match_contract(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    initial_stage = write_stage(
        package_dir,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        ),
    )
    manager = PassManager(package_dir=package_dir, stages=[initial_stage], current_stage="s00")
    contract = PassContract.analysis(
        pass_id="pkg::warp_role_plan@1",
        owner="pkg",
        analysis_produces=(
            AnalysisOutput(
                analysis_id="pkg::WarpRolePlan@1",
                schema="htp.analysis.warp_role_plan.v1",
                path_hint="analysis/warp_role_plan.json",
            ),
        ),
    )

    with pytest.raises(ValueError, match="runnable_py does not match contract"):
        manager.run(
            contract,
            lambda stage_before: PassResult(
                runnable_py=RunnablePySpec(status="stubbed", modes=("sim",)),
                analyses={
                    "analysis/warp_role_plan.json": {"schema": "htp.analysis.warp_role_plan.v1"},
                },
            ),
        )
