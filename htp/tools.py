from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from htp.agent_policy import load_agent_policy
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
    golden_package_dir: Path | str | None = None,
    policy_path: Path | str | None = None,
) -> dict[str, Any]:
    package_path = Path(package_dir)
    policy = load_agent_policy(policy_path)
    binding = bind(package_path)
    validation = binding.validate()
    replay = binding.load(mode=mode).replay(str(load_manifest(package_path)["stages"]["current"]), mode=mode)
    golden_diff = None
    if golden_package_dir is not None:
        golden_diff = semantic_diff(golden_package_dir, package_path)
    report = {
        "ok": validation.ok and replay.ok and (golden_diff is None or golden_diff["equal"]),
        "gates": {
            "validate": validation.ok,
            "replay": replay.ok,
            **({"golden_diff": bool(golden_diff["equal"])} if golden_diff is not None else {}),
        },
        "diagnostics": {
            "validate": list(validation.diagnostics),
            "replay": list(replay.diagnostics),
            **({"golden_diff": golden_diff["details"]} if golden_diff is not None else {}),
        },
        "evidence": {
            "replay_log": replay.log_path,
            "stage_id": replay.stage_id,
            **({"golden_diff": golden_diff} if golden_diff is not None else {}),
        },
        "policy": policy,
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
    details: dict[str, dict[str, Any]] = {}

    if left_manifest.get("target") != right_manifest.get("target"):
        changed_sections.append("manifest.target")
        details["manifest.target"] = _summarize_difference(
            left_manifest.get("target"), right_manifest.get("target")
        )
    if left_manifest.get("outputs") != right_manifest.get("outputs"):
        changed_sections.append("manifest.outputs")
        details["manifest.outputs"] = _summarize_difference(
            left_manifest.get("outputs"), right_manifest.get("outputs")
        )
    if left_manifest.get("extensions") != right_manifest.get("extensions"):
        changed_sections.append("manifest.extensions")
        details["manifest.extensions"] = _summarize_difference(
            left_manifest.get("extensions"), right_manifest.get("extensions")
        )

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
            section = f"current_stage.{semantic_name}"
            changed_sections.append(section)
            details[section] = _summarize_difference(left_payload, right_payload)

    return {
        "equal": not changed_sections,
        "changed_sections": changed_sections,
        "stage_ids": {"left": resolved_left_stage, "right": resolved_right_stage},
        "details": details,
    }


def explain_diagnostic(code: str) -> dict[str, Any]:
    return dict(explain_diagnostic_code(code))


def bisect_stages(
    left_package_dir: Path | str,
    right_package_dir: Path | str,
) -> dict[str, Any]:
    left_root = Path(left_package_dir)
    right_root = Path(right_package_dir)
    left_manifest = load_manifest(left_root)
    right_manifest = load_manifest(right_root)
    left_graph = [stage for stage in left_manifest["stages"]["graph"]]
    right_graph = [stage for stage in right_manifest["stages"]["graph"]]
    shared_len = min(len(left_graph), len(right_graph))

    for index in range(shared_len):
        left_stage = str(left_graph[index]["id"])
        right_stage = str(right_graph[index]["id"])
        diff = semantic_diff(
            left_root,
            right_root,
            left_stage_id=left_stage,
            right_stage_id=right_stage,
        )
        if not diff["equal"]:
            return {
                "equal": False,
                "first_divergent_stage": {"left": left_stage, "right": right_stage},
                "reason": diff,
            }

    return {
        "equal": len(left_graph) == len(right_graph),
        "first_divergent_stage": None
        if len(left_graph) == len(right_graph)
        else {
            "left": str(left_graph[shared_len]["id"]) if shared_len < len(left_graph) else None,
            "right": str(right_graph[shared_len]["id"]) if shared_len < len(right_graph) else None,
        },
        "reason": {
            "changed_sections": ["manifest.stages.graph"],
            "details": {
                "manifest.stages.graph": {
                    "left_count": len(left_graph),
                    "right_count": len(right_graph),
                }
            },
        },
    }


def minimize_package(
    package_dir: Path | str,
    output_dir: Path | str,
    *,
    stage_id: str | None = None,
    include_build: bool = False,
) -> dict[str, Any]:
    source_dir = Path(package_dir)
    target_dir = Path(output_dir)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)

    manifest_path = target_dir / "manifest.json"
    manifest = load_manifest(target_dir)
    selected_stage = stage_id or str(manifest["stages"]["current"])
    graph = manifest["stages"]["graph"]
    keep_ids: list[str] = []
    for stage in graph:
        keep_ids.append(str(stage["id"]))
        if str(stage["id"]) == selected_stage:
            break
    manifest["stages"]["current"] = selected_stage
    manifest["stages"]["graph"] = [stage for stage in graph if str(stage["id"]) in keep_ids]

    ir_root = target_dir / "ir" / "stages"
    for stage_dir in ir_root.iterdir():
        if stage_dir.is_dir() and stage_dir.name not in keep_ids:
            shutil.rmtree(stage_dir)
    if not include_build and (target_dir / "build").exists():
        shutil.rmtree(target_dir / "build")
    if (target_dir / "logs").exists():
        shutil.rmtree(target_dir / "logs")

    extensions = dict(manifest.get("extensions", {}))
    agent_extension = dict(extensions.get("agent", {}))
    agent_extension["minimized_from"] = str(source_dir)
    agent_extension["minimized_stage"] = selected_stage
    extensions["agent"] = agent_extension
    manifest["extensions"] = extensions
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return {
        "ok": True,
        "output_dir": str(target_dir),
        "stage_id": selected_stage,
        "kept_stages": keep_ids,
    }


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
            "policy": dict(report.get("policy", {})),
            "patch_summary": report.get("patch_summary", {"kind": "verification-only"}),
            "decision_trace": report.get("decision_trace", []),
            "attempted_candidates": report.get("attempted_candidates", []),
            "rejected_candidates": report.get("rejected_candidates", []),
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
    semantic = stage.get("semantic", {})
    if isinstance(semantic, dict):
        relpath = semantic.get(semantic_key)
        if isinstance(relpath, str) and (package_root / relpath).exists():
            return json.loads((package_root / relpath).read_text())
    fallback = package_root / "ir" / "stages" / stage_id / f"{semantic_key}.json"
    if fallback.exists():
        return json.loads(fallback.read_text())
    return {}


def _summarize_difference(left: Any, right: Any) -> dict[str, Any]:
    if isinstance(left, dict) and isinstance(right, dict):
        left_keys = set(left)
        right_keys = set(right)
        changed = sorted(key for key in left_keys & right_keys if left[key] != right[key])
        return {
            "kind": "mapping",
            "added_keys": sorted(right_keys - left_keys),
            "removed_keys": sorted(left_keys - right_keys),
            "changed_keys": changed,
        }
    if isinstance(left, list) and isinstance(right, list):
        return {
            "kind": "sequence",
            "left_len": len(left),
            "right_len": len(right),
            "equal_prefix": _equal_prefix_len(left, right),
        }
    return {
        "kind": "value",
        "left": left,
        "right": right,
    }


def _equal_prefix_len(left: list[Any], right: list[Any]) -> int:
    count = 0
    for left_item, right_item in zip(left, right):
        if left_item != right_item:
            break
        count += 1
    return count


__all__ = [
    "bisect_stages",
    "explain_diagnostic",
    "minimize_package",
    "replay_package",
    "semantic_diff",
    "verify_package",
]
