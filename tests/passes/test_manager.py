import json

import pytest

from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.artifacts.state import load_stage_state
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
            "preserved_capabilities": [],
            "added_analyses": [],
            "removed_analyses": [],
            "preserved_analyses": [],
            "added_layout_invariants": [],
            "removed_layout_invariants": [],
            "preserved_layout_invariants": [],
            "added_effect_invariants": [],
            "removed_effect_invariants": [],
            "preserved_effect_invariants": [],
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
            "preserves_python_renderability": True,
            "preserves_python_executability": True,
        },
        "dumps": {
            "program": "ir/stages/s01/program.py",
            "stage": "ir/stages/s01/stage.json",
            "state": "ir/stages/s01/state.json",
            "stubs": None,
        },
        "maps": {},
        "diagnostics": [],
    }


def test_pass_manager_normalizes_stage_maps(tmp_path):
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
    contract = PassContract(
        pass_id="pkg::mlir_import@1",
        owner="pkg",
        kind="transform",
        ast_effect="mutates",
    )

    stage_record = manager.run(
        contract,
        lambda stage_before: PassResult(
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
            entity_map_payload={
                "schema": "htp.entity_map.v1",
                "entities": [{"before": "demo:E1", "after": ["demo:E0"], "reason": "rebind"}],
            },
            binding_map_payload={
                "schema": "htp.binding_map.v1",
                "bindings": [{"before": "demo:S0:B1", "after": ["demo:S0:B0"], "reason": "rebind"}],
            },
        ),
    )

    state_payload = load_stage_state(
        package_dir,
        {"stages": {"graph": [stage_record]}},
        str(stage_record["id"]),
    )
    identity = state_payload["identity"]
    entity_map = identity["entity_map"]
    binding_map = identity["binding_map"]

    assert entity_map["pass_id"] == "pkg::mlir_import@1"
    assert entity_map["stage_before"] == "s00"
    assert entity_map["stage_after"] == "s01"
    assert binding_map["pass_id"] == "pkg::mlir_import@1"
    assert binding_map["stage_before"] == "s00"
    assert binding_map["stage_after"] == "s01"


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


def test_pass_manager_threads_island_records_into_stage_graph(tmp_path):
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
    contract = PassContract(
        pass_id="pkg::mlir_roundtrip@1",
        owner="pkg",
        kind="mixed",
        ast_effect="mutates",
    )

    stage_record = manager.run(
        contract,
        lambda stage_before: PassResult(
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
            islands=({"island_id": "mlir_cse", "dir": "ir/stages/s01/islands/mlir_cse"},),
        ),
    )

    assert stage_record["islands"] == [{"island_id": "mlir_cse", "dir": "ir/stages/s01/islands/mlir_cse"}]
