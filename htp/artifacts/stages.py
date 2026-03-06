from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from htp.schemas import IDS_BINDINGS_SCHEMA_ID, IDS_ENTITIES_SCHEMA_ID, REPLAY_STUBS_SCHEMA_ID

from .validate import validate_path_component, validate_runnable_py

ANALYSIS_INDEX_SCHEMA_ID = "htp.analysis.index.v1"


@dataclass(frozen=True)
class AnalysisSpec:
    analysis_id: str
    schema: str
    filename: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class RunnablePySpec:
    status: str
    modes: tuple[str, ...]
    program_text: str = ""
    stubs_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    pass_id: str | None
    runnable_py: RunnablePySpec
    analyses: tuple[AnalysisSpec, ...] = ()
    entities_payload: dict[str, Any] = field(default_factory=dict)
    bindings_payload: dict[str, Any] = field(default_factory=dict)
    entity_map_payload: dict[str, Any] | None = None
    binding_map_payload: dict[str, Any] | None = None
    summary_payload: dict[str, Any] | None = None
    digests: dict[str, str | None] = field(default_factory=dict)


def write_stage(package_dir: Path, stage: StageSpec) -> dict[str, object]:
    validate_path_component(field_name="stage.stage_id", value=stage.stage_id)
    validate_runnable_py(
        status=stage.runnable_py.status,
        modes=stage.runnable_py.modes,
        has_stubs=stage.runnable_py.stubs_payload is not None,
    )
    for analysis in stage.analyses:
        validate_path_component(field_name="analysis.filename", value=analysis.filename)

    stage_dir = Path(package_dir) / "ir" / "stages" / stage.stage_id
    analysis_dir = stage_dir / "analysis"
    ids_dir = stage_dir / "ids"
    maps_dir = stage_dir / "maps"
    replay_dir = stage_dir / "replay"

    analysis_dir.mkdir(parents=True, exist_ok=True)
    ids_dir.mkdir(parents=True, exist_ok=True)

    _write_text(stage_dir / "program.py", _program_text(stage))
    _write_json(stage_dir / "summary.json", _summary_payload(stage))
    _write_json(stage_dir / "ids" / "entities.json", _entities_payload(stage))
    _write_json(stage_dir / "ids" / "bindings.json", _bindings_payload(stage))
    _write_json(stage_dir / "analysis" / "index.json", _analysis_index_payload(package_dir, stage))

    if stage.entity_map_payload is not None or stage.binding_map_payload is not None:
        maps_dir.mkdir(parents=True, exist_ok=True)
    if stage.entity_map_payload is not None:
        _write_json(stage_dir / "maps" / "entity_map.json", stage.entity_map_payload)
    if stage.binding_map_payload is not None:
        _write_json(stage_dir / "maps" / "binding_map.json", stage.binding_map_payload)

    if stage.runnable_py.stubs_payload is not None:
        replay_dir.mkdir(parents=True, exist_ok=True)
        stubs_payload = dict(stage.runnable_py.stubs_payload)
        stubs_payload.setdefault("schema", REPLAY_STUBS_SCHEMA_ID)
        _write_json(stage_dir / "replay" / "stubs.json", stubs_payload)

    for analysis in stage.analyses:
        _write_json(stage_dir / "analysis" / analysis.filename, analysis.payload)

    return {
        "id": stage.stage_id,
        "pass": stage.pass_id,
        "dir": _relative_path(stage_dir, package_dir),
        "runnable_py": {
            "status": stage.runnable_py.status,
            "modes": list(stage.runnable_py.modes),
            "program_py": _relative_path(stage_dir / "program.py", package_dir),
            "stubs": (
                _relative_path(stage_dir / "replay" / "stubs.json", package_dir)
                if stage.runnable_py.stubs_payload is not None
                else None
            ),
        },
        "analysis_index": _relative_path(stage_dir / "analysis" / "index.json", package_dir),
        "ids": {
            "entities": _relative_path(stage_dir / "ids" / "entities.json", package_dir),
            "bindings": _relative_path(stage_dir / "ids" / "bindings.json", package_dir),
        },
        "maps": {
            "entity_map": (
                _relative_path(stage_dir / "maps" / "entity_map.json", package_dir)
                if stage.entity_map_payload is not None
                else None
            ),
            "binding_map": (
                _relative_path(stage_dir / "maps" / "binding_map.json", package_dir)
                if stage.binding_map_payload is not None
                else None
            ),
        },
        "islands": [],
        "digests": _digests_payload(stage),
        "summary": _relative_path(stage_dir / "summary.json", package_dir),
    }


def _analysis_index_payload(package_dir: Path, stage: StageSpec) -> dict[str, object]:
    return {
        "schema": ANALYSIS_INDEX_SCHEMA_ID,
        "analyses": [
            {
                "analysis_id": analysis.analysis_id,
                "schema": analysis.schema,
                "path": _relative_path(
                    Path(package_dir) / "ir" / "stages" / stage.stage_id / "analysis" / analysis.filename,
                    package_dir,
                ),
            }
            for analysis in stage.analyses
        ],
    }


def _entities_payload(stage: StageSpec) -> dict[str, Any]:
    if stage.entities_payload:
        return stage.entities_payload
    return {
        "schema": IDS_ENTITIES_SCHEMA_ID,
        "def_id": "",
        "entities": [],
        "node_to_entity": [],
    }


def _bindings_payload(stage: StageSpec) -> dict[str, Any]:
    if stage.bindings_payload:
        return stage.bindings_payload
    return {
        "schema": IDS_BINDINGS_SCHEMA_ID,
        "def_id": "",
        "scopes": [],
        "bindings": [],
        "name_uses": [],
    }


def _summary_payload(stage: StageSpec) -> dict[str, Any]:
    if stage.summary_payload is not None:
        return stage.summary_payload
    return {
        "stage_id": stage.stage_id,
        "pass": stage.pass_id,
        "runnable_py": stage.runnable_py.status,
        "modes": list(stage.runnable_py.modes),
    }


def _digests_payload(stage: StageSpec) -> dict[str, str | None]:
    return {
        "ast_hash": stage.digests.get("ast_hash"),
        "types_hash": stage.digests.get("types_hash"),
        "effects_hash": stage.digests.get("effects_hash"),
        "analysis_hash": stage.digests.get("analysis_hash"),
    }


def _program_text(stage: StageSpec) -> str:
    if stage.runnable_py.program_text:
        return stage.runnable_py.program_text
    lines = [
        f'STAGE_ID = "{stage.stage_id}"',
        f'RUNNABLE_PY = "{stage.runnable_py.status}"',
        f"MODES = {tuple(stage.runnable_py.modes)!r}",
        "",
        "def run(*args, **kwargs):",
        '    raise NotImplementedError("Stage replay is not implemented in v1")',
        "",
    ]
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)


def _relative_path(path: Path, package_dir: Path) -> str:
    return Path(path).relative_to(package_dir).as_posix()


__all__ = [
    "ANALYSIS_INDEX_SCHEMA_ID",
    "AnalysisSpec",
    "RunnablePySpec",
    "StageSpec",
    "write_stage",
]
