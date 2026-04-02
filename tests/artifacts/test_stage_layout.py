import json

import pytest

from htp.artifacts.stages import AnalysisSpec, RunnablePySpec, StageSpec, write_stage
from htp.artifacts.validate import ArtifactValidationError
from htp.ir.dialects import dialect_activation_payload
from htp.ir.program.module import ProgramModule


def test_stubbed_stage_requires_replay_stubs_path(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    with pytest.raises(ArtifactValidationError, match="replay/stubs.json"):
        write_stage(
            package_dir,
            StageSpec(
                stage_id="s02",
                pass_id="pkg::lower@1",
                runnable_py=RunnablePySpec(status="stubbed", modes=("sim",)),
            ),
        )


def test_stage_without_analyses_emits_compact_stage_contract(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    write_stage(
        package_dir,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        ),
    )

    assert json.loads((package_dir / "ir/stages/s00/stage.json").read_text()) == {
        "schema": "htp.stage.v2",
        "stage_id": "s00",
        "pass_id": None,
        "entrypoints": [
            {
                "name": "run",
                "kind": "stage_run",
                "interpreter_id": "htp.interpreter.snapshot.v1",
            }
        ],
        "dialects": {"active": [], "activation": {}},
        "executability": {"status": "preserves", "modes": ["sim"]},
        "aspect_inventory": ["effects", "layout", "schedule", "types"],
        "analysis_inventory": [],
        "rewrite_maps": {"entity_map": False, "binding_map": False},
        "paths": {
            "program": "ir/stages/s00/program.py",
            "state": "ir/stages/s00/state.json",
        },
        "diagnostics": [],
    }
    assert json.loads((package_dir / "ir/stages/s00/state.json").read_text()) == {
        "schema": "htp.program_module.v1",
        "items": {
            "canonical_ast": {"schema": "htp.program_ast.v1", "program": {}},
            "kernel_ir": {},
            "workload_ir": {},
        },
        "aspects": {
            "types": {},
            "layout": {},
            "effects": {},
            "schedule": {},
        },
        "analyses": {},
        "identity": {
            "entities": {},
            "bindings": {},
            "entity_map": None,
            "binding_map": None,
        },
        "entrypoints": [
            {
                "name": "run",
                "kind": "stage_run",
                "interpreter_id": "htp.interpreter.snapshot.v1",
            }
        ],
        "meta": {},
    }


@pytest.mark.parametrize(
    ("stage_id", "message"),
    [
        ("../s00", "stage.stage_id"),
        ("s/00", "stage.stage_id"),
    ],
)
def test_stage_rejects_unsafe_stage_id(tmp_path, stage_id, message):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    with pytest.raises(ArtifactValidationError, match=message):
        write_stage(
            package_dir,
            StageSpec(
                stage_id=stage_id,
                pass_id=None,
                runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
            ),
        )


def test_stage_rejects_unsafe_analysis_filename(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    with pytest.raises(ArtifactValidationError, match="analysis.filename"):
        write_stage(
            package_dir,
            StageSpec(
                stage_id="s00",
                pass_id=None,
                runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
                analyses=(
                    AnalysisSpec(
                        analysis_id="pkg::analysis@1",
                        schema="htp.analysis.example.v1",
                        filename="../escape.json",
                        payload={"ok": True},
                    ),
                ),
            ),
        )


def test_stage_rejects_unsupported_runnable_mode(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    with pytest.raises(ArtifactValidationError, match="subset"):
        write_stage(
            package_dir,
            StageSpec(
                stage_id="s00",
                pass_id=None,
                runnable_py=RunnablePySpec(status="preserves", modes=("sim", "host")),
            ),
        )


def test_stage_summary_records_active_dialects(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    module = ProgramModule.from_program_dict(
        {
            "entry": "run",
            "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": "run"}},
            "kernel_ir": {},
            "workload_ir": {},
        },
        meta=dialect_activation_payload("htp.wsp"),
    )

    write_stage(
        package_dir,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
            program_module_payload=module.to_payload(),
        ),
    )

    stage_json = json.loads((package_dir / "ir/stages/s00/stage.json").read_text())

    assert stage_json["dialects"]["active"] == ["htp.core", "htp.kernel", "htp.wsp"]
    assert stage_json["dialects"]["activation"]["requested"] == ["htp.wsp"]
