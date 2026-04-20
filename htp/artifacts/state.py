from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def load_stage_record(manifest: Mapping[str, Any], stage_id: str) -> Mapping[str, Any]:
    return next(stage for stage in manifest["stages"]["graph"] if str(stage["id"]) == stage_id)


def load_stage_state(package_root: Path | str, manifest: Mapping[str, Any], stage_id: str) -> dict[str, Any]:
    root = Path(package_root)
    stage = load_stage_record(manifest, stage_id)
    relpath = stage.get("state")
    if isinstance(relpath, str) and (root / relpath).exists():
        return json.loads((root / relpath).read_text())
    fallback = root / "ir" / "stages" / stage_id / "state.json"
    if fallback.exists():
        return json.loads(fallback.read_text())
    return {}


def stage_state_relpath(manifest: Mapping[str, Any], stage_id: str) -> str:
    stage = load_stage_record(manifest, stage_id)
    relpath = stage.get("state")
    if isinstance(relpath, str):
        return relpath
    return f"ir/stages/{stage_id}/state.json"


def state_section(state: Mapping[str, Any], section: str) -> dict[str, Any]:
    if section == "kernel_ir":
        return _as_mapping(_as_mapping(state.get("items", {})).get("kernel_ir", {}))
    if section == "workload_ir":
        return _as_mapping(_as_mapping(state.get("items", {})).get("workload_ir", {}))
    if section == "canonical_ast":
        return _as_mapping(_as_mapping(state.get("items", {})).get("canonical_ast", {}))
    if section in {"types", "layout", "effects", "schedule"}:
        return _as_mapping(_as_mapping(state.get("aspects", {})).get(section, {}))
    if section == "identity":
        return _as_mapping(state.get("identity", {}))
    if section == "analyses":
        return _as_mapping(state.get("analyses", {}))
    raise KeyError(f"Unknown stage state section: {section}")


def state_ref(manifest: Mapping[str, Any], stage_id: str, pointer: str) -> str:
    return f"{stage_state_relpath(manifest, stage_id)}#{pointer}"


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


__all__ = [
    "load_stage_record",
    "load_stage_state",
    "stage_state_relpath",
    "state_ref",
    "state_section",
]
