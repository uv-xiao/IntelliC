import json
from pathlib import Path

import htp
import htp.bindings
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage


def test_replay_result_contains_log_and_stage_id(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()

    stage_record = write_stage(
        package_dir,
        StageSpec(
            stage_id="s01",
            pass_id="pkg::lower@1",
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text="""
STAGE_ID = "s01"

def run(*args, **kwargs):
    return {"args": list(args), "kwargs": kwargs}
""".lstrip(),
            ),
        ),
    )
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "htp.manifest.v1",
                "target": {
                    "backend": "pto",
                    "variant": "a2a3sim",
                },
                "stages": {
                    "current": "s01",
                    "graph": [stage_record],
                },
            },
            indent=2,
        )
        + "\n"
    )

    binding = htp.bind(package_dir)
    session = binding.load(mode="sim")
    result = session.replay("s01", args=(1, 2), kwargs={"flag": True})

    assert result.ok is True
    assert result.stage_id == "s01"
    assert result.result == {"args": [1, 2], "kwargs": {"flag": True}}
    assert result.log_path is not None
    assert Path(package_dir / result.log_path).is_file()
