import json

import pytest

from htp.artifacts.stages import AnalysisSpec, RunnablePySpec, StageSpec, write_stage
from htp.artifacts.validate import ArtifactValidationError


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


def test_stage_without_analyses_emits_empty_analysis_index(tmp_path):
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

    assert json.loads((package_dir / "ir/stages/s00/analysis/index.json").read_text()) == {
        "schema": "htp.analysis.index.v1",
        "analyses": [],
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
