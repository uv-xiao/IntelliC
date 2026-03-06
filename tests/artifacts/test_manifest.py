import json

import pytest

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.artifacts.validate import ArtifactValidationError
from htp.schemas import MANIFEST_SCHEMA_ID


def test_manifest_contains_normalized_stage_records(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    capture = StageSpec(
        stage_id="s00",
        pass_id=None,
        runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
    )
    lowered = StageSpec(
        stage_id="s01",
        pass_id="pkg::lower@1",
        runnable_py=RunnablePySpec(
            status="stubbed",
            modes=("sim", "device"),
            stubs_payload={"schema": "htp.replay.stubs.v1", "stubs": []},
        ),
    )

    capture_record = write_stage(package_dir, capture)
    lowered_record = write_stage(package_dir, lowered)
    manifest = write_manifest(
        package_dir,
        current_stage="s01",
        stages=[capture_record, lowered_record],
    )

    assert manifest == json.loads((package_dir / "manifest.json").read_text())
    assert manifest["schema"] == MANIFEST_SCHEMA_ID
    assert manifest["stages"]["current"] == "s01"
    assert manifest["stages"]["graph"] == [
        {
            "id": "s00",
            "pass": None,
            "dir": "ir/stages/s00",
            "runnable_py": {
                "status": "preserves",
                "modes": ["sim"],
                "program_py": "ir/stages/s00/program.py",
                "stubs": None,
            },
            "analysis_index": "ir/stages/s00/analysis/index.json",
            "ids": {
                "entities": "ir/stages/s00/ids/entities.json",
                "bindings": "ir/stages/s00/ids/bindings.json",
            },
            "maps": {
                "entity_map": None,
                "binding_map": None,
            },
            "islands": [],
            "digests": {
                "ast_hash": None,
                "types_hash": None,
                "effects_hash": None,
                "analysis_hash": None,
            },
            "summary": "ir/stages/s00/summary.json",
        },
        {
            "id": "s01",
            "pass": "pkg::lower@1",
            "dir": "ir/stages/s01",
            "runnable_py": {
                "status": "stubbed",
                "modes": ["sim", "device"],
                "program_py": "ir/stages/s01/program.py",
                "stubs": "ir/stages/s01/replay/stubs.json",
            },
            "analysis_index": "ir/stages/s01/analysis/index.json",
            "ids": {
                "entities": "ir/stages/s01/ids/entities.json",
                "bindings": "ir/stages/s01/ids/bindings.json",
            },
            "maps": {
                "entity_map": None,
                "binding_map": None,
            },
            "islands": [],
            "digests": {
                "ast_hash": None,
                "types_hash": None,
                "effects_hash": None,
                "analysis_hash": None,
            },
            "summary": "ir/stages/s01/summary.json",
        },
    ]


def test_manifest_rejects_duplicate_stage_ids(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    stage_record = write_stage(
        package_dir,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        ),
    )

    with pytest.raises(ArtifactValidationError, match="Duplicate stage ids"):
        write_manifest(
            package_dir,
            current_stage="s00",
            stages=[stage_record, dict(stage_record)],
        )
