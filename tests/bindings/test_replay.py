import json
from pathlib import Path

import htp
import htp.bindings
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.schemas import BINDING_LOG_SCHEMA_ID


def _write_manifest(package_dir, *, current_stage="s01", stage_records=None):
    if stage_records is None:
        stage_records = []
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "htp.manifest.v1",
                "target": {
                    "backend": "pto",
                    "variant": "a2a3sim",
                },
                "stages": {
                    "current": current_stage,
                    "graph": stage_records,
                },
            },
            indent=2,
        )
        + "\n"
    )


def _write_stage(package_dir, *, stage_id="s01", program_text, modes=("sim",)):
    return write_stage(
        package_dir,
        StageSpec(
            stage_id=stage_id,
            pass_id="pkg::lower@1",
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=modes,
                program_text=program_text,
            ),
        ),
    )


def test_replay_result_contains_log_and_stage_id(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()

    stage_record = _write_stage(
        package_dir,
        program_text="""
STAGE_ID = "s01"

def run(*args, **kwargs):
    return {"args": list(args), "kwargs": kwargs}
""".lstrip(),
    )
    _write_manifest(package_dir, stage_records=[stage_record])

    binding = htp.bind(package_dir)
    session = binding.load(mode="sim")
    result = session.replay("s01", args=(1, 2), kwargs={"flag": True})

    assert result.ok is True
    assert result.stage_id == "s01"
    assert result.result == {"args": [1, 2], "kwargs": {"flag": True}}
    assert result.log_path is not None
    assert Path(package_dir / result.log_path).is_file()
    assert json.loads((package_dir / result.log_path).read_text()) == {
        "schema": BINDING_LOG_SCHEMA_ID,
        "kind": "replay",
        "fields": {
            "backend": "pto",
            "mode": "sim",
            "stage_id": "s01",
            "entry": "run",
            "trace": "basic",
            "ok": "True",
            "diagnostic_codes": "",
        },
    }


def test_replay_returns_structured_diagnostic_for_missing_stage(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    _write_manifest(package_dir, stage_records=[])

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("missing")

    assert result.ok is False
    assert result.stage_id == "missing"
    assert result.diagnostics[0]["code"] == "HTP.BINDINGS.STAGE_NOT_FOUND"


def test_replay_returns_structured_diagnostic_for_import_failure(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    stage_record = _write_stage(
        package_dir,
        program_text="def run(:\n    pass\n",
    )
    _write_manifest(package_dir, stage_records=[stage_record])

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("s01")

    assert result.ok is False
    assert result.diagnostics[0]["code"] == "HTP.BINDINGS.REPLAY_LOAD_ERROR"


def test_replay_returns_structured_diagnostic_for_missing_entrypoint(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    stage_record = _write_stage(
        package_dir,
        program_text="""
def run(*args, **kwargs):
    return "ok"
""".lstrip(),
    )
    _write_manifest(package_dir, stage_records=[stage_record])

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("s01", entry="missing")

    assert result.ok is False
    assert result.entry == "missing"
    assert result.diagnostics[0]["code"] == "HTP.BINDINGS.MISSING_ENTRYPOINT"


def test_replay_converts_stub_hits_into_structured_diagnostics(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    stage_record = _write_stage(
        package_dir,
        program_text="""
from htp.runtime import raise_stub

def run(*args, **kwargs):
    raise_stub(
        "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
        node_id="node.intrinsic.7",
        entity_id="demo.intrinsic",
        kind="intrinsic",
        artifact_ref="ir/stages/s01/replay/stubs.json",
        detail="No simulator registered for demo.intrinsic",
    )
""".lstrip(),
    )
    _write_manifest(package_dir, stage_records=[stage_record])

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("s01")

    assert result.ok is False
    assert result.diagnostics[0]["code"] == "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
    assert result.diagnostics[0]["node_id"] == "node.intrinsic.7"
    assert result.diagnostics[0]["artifact_ref"] == "ir/stages/s01/replay/stubs.json"
    assert result.diagnostics[0]["payload_ref"] == "ir/stages/s01/replay/stubs.json"
    assert result.diagnostics[0]["fix_hints_ref"] == "docs/design/layers/04_artifacts_replay_debug.md"
    assert result.trace_ref == "ir/stages/s01/replay/stubs.json"


def test_run_returns_structured_diagnostic_for_stage_execution_exception(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    stage_record = _write_stage(
        package_dir,
        program_text="""
def run(*args, **kwargs):
    raise ValueError("boom")
""".lstrip(),
    )
    _write_manifest(package_dir, stage_records=[stage_record])

    session = htp.bind(package_dir).load(mode="sim")
    result = session.run("run")

    assert result.ok is False
    assert result.entry == "run"
    assert result.diagnostics[0]["code"] == "HTP.BINDINGS.RUN_EXECUTION_ERROR"
    assert result.log_path is not None


def test_replay_logs_use_unique_filenames(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    stage_record = _write_stage(
        package_dir,
        program_text="""
def run(*args, **kwargs):
    return "ok"
""".lstrip(),
    )
    _write_manifest(package_dir, stage_records=[stage_record])

    session = htp.bind(package_dir).load(mode="sim")
    first = session.replay("s01")
    second = session.replay("s01")

    assert first.log_path != second.log_path


def test_binding_validate_reports_malformed_manifest_sections(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    stage_record = _write_stage(
        package_dir,
        program_text="""
def run(*args, **kwargs):
    return "ok"
""".lstrip(),
    )
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "htp.manifest.v1",
                "target": {"backend": "pto", "variant": "a2a3sim"},
                "inputs": "bad",
                "pipeline": {"pass_ids": "bad"},
                "capabilities": [],
                "stages": {"current": "s01", "graph": [stage_record]},
            },
            indent=2,
        )
        + "\n"
    )

    result = htp.bind(package_dir).validate()

    assert result.ok is False
    assert [item["code"] for item in result.diagnostics].count("HTP.BINDINGS.MALFORMED_MANIFEST_SECTION") == 3


def test_binding_validate_reports_invalid_stage_schema(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    stage_record = _write_stage(
        package_dir,
        program_text="""
def run(*args, **kwargs):
    return "ok"
""".lstrip(),
    )
    program_ast_path = package_dir / stage_record["program_pyast"]
    payload = json.loads(program_ast_path.read_text())
    payload["schema"] = "wrong.schema"
    program_ast_path.write_text(json.dumps(payload, indent=2) + "\n")
    _write_manifest(package_dir, stage_records=[stage_record])

    result = htp.bind(package_dir).validate()

    assert result.ok is False
    assert {
        "code": "HTP.BINDINGS.INVALID_SCHEMA",
        "detail": f"{stage_record['program_pyast']} must declare schema 'htp.program_ast.v1'.",
    } in result.diagnostics


def test_replay_returns_structured_diagnostic_for_malformed_stages_shape(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "htp.manifest.v1",
                "target": {"backend": "pto", "variant": "a2a3sim"},
                "stages": "broken",
            },
            indent=2,
        )
        + "\n"
    )

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("s01")

    assert result.ok is False
    assert result.diagnostics[0]["code"] == "HTP.BINDINGS.MALFORMED_STAGE_GRAPH"


def test_replay_returns_structured_diagnostic_for_malformed_runnable_py_shape(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    _write_manifest(
        package_dir,
        stage_records=[
            {
                "id": "s01",
                "runnable_py": ["not", "a", "mapping"],
            }
        ],
    )

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("s01")

    assert result.ok is False
    assert result.diagnostics[0]["code"] == "HTP.BINDINGS.MALFORMED_RUNNABLE_PY"


def test_replay_returns_structured_diagnostic_for_malformed_runnable_modes_shape(tmp_path):
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    _write_manifest(
        package_dir,
        stage_records=[
            {
                "id": "s01",
                "runnable_py": {
                    "program_py": "ir/stages/s01/program.py",
                    "modes": None,
                },
            }
        ],
    )

    session = htp.bind(package_dir).load(mode="sim")
    result = session.replay("s01")

    assert result.ok is False
    assert result.diagnostics[0]["code"] == "HTP.BINDINGS.MALFORMED_RUNNABLE_MODES"
