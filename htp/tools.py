from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from htp.bindings import bind
from htp.bindings.base import ReplayResult
from htp.bindings.validate import load_manifest
from htp.diagnostics import explain as explain_diagnostic_code


def replay_package(
    package_dir: Path | str,
    *,
    stage_id: str | None = None,
    entry: str | None = None,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    mode: str = "sim",
) -> ReplayResult:
    package_path = Path(package_dir)
    manifest = load_manifest(package_path)
    resolved_stage = stage_id or str(manifest["stages"]["current"])
    session = bind(package_path).load(mode=mode)
    return session.replay(
        resolved_stage,
        entry=entry,
        args=args,
        kwargs=kwargs,
        mode=mode,
    )


def verify_package(
    package_dir: Path | str,
    *,
    goal: str = "verify",
    mode: str = "sim",
) -> dict[str, Any]:
    package_path = Path(package_dir)
    binding = bind(package_path)
    validation = binding.validate()
    replay = binding.load(mode=mode).replay(str(load_manifest(package_path)["stages"]["current"]), mode=mode)
    report = {
        "ok": validation.ok and replay.ok,
        "gates": {
            "validate": validation.ok,
            "replay": replay.ok,
        },
        "diagnostics": {
            "validate": list(validation.diagnostics),
            "replay": list(replay.diagnostics),
        },
        "evidence": {
            "replay_log": replay.log_path,
            "stage_id": replay.stage_id,
        },
    }
    _record_agent_provenance(package_path, goal=goal, report=report)
    return report


def semantic_diff(
    left_package_dir: Path | str,
    right_package_dir: Path | str,
    *,
    left_stage_id: str | None = None,
    right_stage_id: str | None = None,
) -> dict[str, Any]:
    left_root = Path(left_package_dir)
    right_root = Path(right_package_dir)
    left_manifest = load_manifest(left_root)
    right_manifest = load_manifest(right_root)
    resolved_left_stage = left_stage_id or str(left_manifest["stages"]["current"])
    resolved_right_stage = right_stage_id or str(right_manifest["stages"]["current"])
    changed_sections: list[str] = []

    if left_manifest.get("target") != right_manifest.get("target"):
        changed_sections.append("manifest.target")
    if left_manifest.get("outputs") != right_manifest.get("outputs"):
        changed_sections.append("manifest.outputs")
    if left_manifest.get("extensions") != right_manifest.get("extensions"):
        changed_sections.append("manifest.extensions")

    for semantic_name, relpath_key in (
        ("kernel_ir", "kernel_ir"),
        ("workload_ir", "workload_ir"),
        ("types", "types"),
        ("layout", "layout"),
        ("effects", "effects"),
        ("schedule", "schedule"),
    ):
        left_payload = _load_stage_semantic(left_root, left_manifest, resolved_left_stage, relpath_key)
        right_payload = _load_stage_semantic(right_root, right_manifest, resolved_right_stage, relpath_key)
        if left_payload != right_payload:
            changed_sections.append(f"current_stage.{semantic_name}")

    return {
        "equal": not changed_sections,
        "changed_sections": changed_sections,
        "stage_ids": {"left": resolved_left_stage, "right": resolved_right_stage},
    }


def explain_diagnostic(code: str) -> dict[str, Any]:
    return dict(explain_diagnostic_code(code))


def _record_agent_provenance(package_dir: Path, *, goal: str, report: dict[str, Any]) -> None:
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    extensions = dict(manifest.get("extensions", {}))
    agent_extension = dict(extensions.get("agent", {}))
    agent_extension.update(
        {
            "run_id": uuid4().hex,
            "goal": goal,
            "gates": dict(report["gates"]),
            "evidence": dict(report["evidence"]),
        }
    )
    extensions["agent"] = agent_extension
    manifest["extensions"] = extensions
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def _load_stage_semantic(
    package_root: Path,
    manifest: dict[str, Any],
    stage_id: str,
    semantic_key: str,
) -> dict[str, Any]:
    stage = next(stage for stage in manifest["stages"]["graph"] if stage["id"] == stage_id)
    relpath = stage["semantic"][semantic_key]
    return json.loads((package_root / relpath).read_text())


__all__ = [
    "explain_diagnostic",
    "replay_package",
    "semantic_diff",
    "verify_package",
]
