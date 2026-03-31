from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from htp.ir.module import PROGRAM_MODULE_SCHEMA_ID, ProgramModule
from htp.ir.render import render_program_module_payload
from htp.schemas import REPLAY_STUBS_SCHEMA_ID

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
    islands: tuple[dict[str, str], ...] = ()
    program_module_payload: dict[str, Any] = field(default_factory=dict)
    entity_map_payload: dict[str, Any] | None = None
    binding_map_payload: dict[str, Any] | None = None
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
    replay_dir = stage_dir / "replay"

    analysis_dir.mkdir(parents=True, exist_ok=True)

    _write_text(stage_dir / "program.py", _program_text(stage))
    _write_json(stage_dir / "stage.json", _stage_summary_payload(package_dir, stage))
    _write_json(stage_dir / "state.json", _state_payload(stage))

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
        "program": _relative_path(stage_dir / "program.py", package_dir),
        "stage": _relative_path(stage_dir / "stage.json", package_dir),
        "state": _relative_path(stage_dir / "state.json", package_dir),
        "rewrite_maps": {
            "entity_map": stage.entity_map_payload is not None,
            "binding_map": stage.binding_map_payload is not None,
        },
        "islands": [dict(island) for island in stage.islands],
        "digests": _digests_payload(stage),
    }


def _program_module_payload(stage: StageSpec) -> dict[str, Any]:
    if stage.program_module_payload:
        return stage.program_module_payload
    return ProgramModule.from_program_dict({}).to_payload()


def _state_payload(stage: StageSpec) -> dict[str, Any]:
    payload = dict(_program_module_payload(stage))
    identity = _as_mapping(payload.get("identity", {}))
    if stage.entity_map_payload is not None:
        identity["entity_map"] = dict(stage.entity_map_payload)
    if stage.binding_map_payload is not None:
        identity["binding_map"] = dict(stage.binding_map_payload)
    if identity:
        payload["identity"] = identity
    payload.setdefault("schema", PROGRAM_MODULE_SCHEMA_ID)
    return payload


def _stage_summary_payload(package_dir: Path, stage: StageSpec) -> dict[str, Any]:
    stage_dir = Path(package_dir) / "ir" / "stages" / stage.stage_id
    state_payload = _state_payload(stage)
    return {
        "schema": "htp.stage.v2",
        "stage_id": stage.stage_id,
        "pass_id": stage.pass_id,
        "entrypoints": list(state_payload.get("entrypoints", [])),
        "dialects": _dialect_summary(_as_mapping(state_payload.get("meta", {}))),
        "executability": {
            "status": stage.runnable_py.status,
            "modes": list(stage.runnable_py.modes),
        },
        "aspect_inventory": sorted(_as_mapping(state_payload.get("aspects", {})).keys()),
        "analysis_inventory": [
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
        "rewrite_maps": {
            "entity_map": stage.entity_map_payload is not None,
            "binding_map": stage.binding_map_payload is not None,
        },
        "paths": {
            "program": _relative_path(stage_dir / "program.py", package_dir),
            "state": _relative_path(stage_dir / "state.json", package_dir),
        },
        "diagnostics": [],
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
    return _render_program_module(stage)


def _render_program_module(stage: StageSpec) -> str:
    return render_program_module_payload(_state_payload(stage))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)


def _relative_path(path: Path, package_dir: Path) -> str:
    return Path(path).relative_to(package_dir).as_posix()


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _dialect_summary(meta: dict[str, Any]) -> dict[str, Any]:
    active = meta.get("active_dialects")
    activation = meta.get("dialect_activation")
    return {
        "active": list(active) if isinstance(active, list) else [],
        "activation": dict(activation) if isinstance(activation, dict) else {},
    }


__all__ = [
    "AnalysisSpec",
    "RunnablePySpec",
    "StageSpec",
    "write_stage",
]
