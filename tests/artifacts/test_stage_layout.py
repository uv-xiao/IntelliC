import json

import pytest

from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
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
