"""User-facing package and workflow tools for replay, verification, and policy checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

from htp.agent_policy import evaluate_edit_policy, load_agent_policy
from htp.bindings import bind
from htp.bindings.base import ReplayResult
from htp.bindings.validate import load_manifest
from htp.diagnostics import explain as explain_diagnostic_code
from htp.perf import compare_perf, load_perf_payload


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
    perf_baseline_dir: Path | str | None = None,
    policy_path: Path | str | None = None,
) -> dict[str, Any]:
    package_path = Path(package_dir)
    policy = load_agent_policy(policy_path)
    binding = bind(package_path)
    validation = binding.validate()
    replay = binding.load(mode=mode).replay(str(load_manifest(package_path)["stages"]["current"]), mode=mode)
    target_suite = binding.correctness_suite(mode=mode)
    golden_diff = None
    if golden_package_dir is not None:
        golden_diff = semantic_diff(golden_package_dir, package_path)
    perf_gate = None
    if policy["perf"].get("enabled"):
        perf_gate = compare_perf(
            load_perf_payload(package_path),
            load_perf_payload(perf_baseline_dir) if perf_baseline_dir is not None else None,
            max_regression_pct=float(policy["perf"]["max_regression_pct"]),
        )
    gates = {
        "validate": validation.ok,
        "replay": replay.ok,
        "target_suite": bool(target_suite["ok"]),
        **({"golden_diff": bool(golden_diff["equal"])} if golden_diff is not None else {}),
        **({"perf": bool(perf_gate["ok"])} if perf_gate is not None else {}),
    }
    report = {
        "ok": all(gates.values()),
        "gates": gates,
        "diagnostics": {
            "validate": list(validation.diagnostics),
            "replay": list(replay.diagnostics),
            "target_suite": list(target_suite["diagnostics"]),
            **({"golden_diff": golden_diff["details"]} if golden_diff is not None else {}),
            **({"perf": perf_gate} if perf_gate is not None else {}),
        },
        "evidence": {
            "replay_log": replay.log_path,
            "stage_id": replay.stage_id,
            "target_suite": target_suite,
            **({"golden_diff": golden_diff} if golden_diff is not None else {}),
            **({"perf": perf_gate} if perf_gate is not None else {}),
        },
        "policy": policy,
    }
    report["promotion_bundle"] = _promotion_bundle(report)
    report["promotion"] = promotion_plan_from_report(report)
    workflow_report_path = _write_workflow_report(package_path, report)
    report["evidence"]["workflow_report"] = workflow_report_path
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
            details[section] = {
                **_summarize_difference(left_payload, right_payload),
                "refs": {
                    "left": _stage_semantic_relpath(left_manifest, resolved_left_stage, relpath_key),
                    "right": _stage_semantic_relpath(right_manifest, resolved_right_stage, relpath_key),
                },
            }
    identity_diff = _identity_aware_stage_diff(
        left_root, right_root, left_manifest, right_manifest, resolved_left_stage, resolved_right_stage
    )
    if not identity_diff["equal"]:
        changed_sections.append("current_stage.identity")
        details["current_stage.identity"] = identity_diff
    replay_stub_diff = _replay_stub_diff(
        left_root, right_root, left_manifest, right_manifest, resolved_left_stage, resolved_right_stage
    )
    if not replay_stub_diff["equal"]:
        changed_sections.append("current_stage.replay_stubs")
        details["current_stage.replay_stubs"] = replay_stub_diff
    pass_trace_diff = _pass_trace_diff(left_root, right_root)
    if not pass_trace_diff["equal"]:
        changed_sections.append("pass_trace")
        details["pass_trace"] = pass_trace_diff

    return {
        "equal": not changed_sections,
        "changed_sections": changed_sections,
        "stage_ids": {"left": resolved_left_stage, "right": resolved_right_stage},
        "details": details,
    }


def explain_diagnostic(code: str) -> dict[str, Any]:
    return dict(explain_diagnostic_code(code))


def promotion_plan(
    package_dir: Path | str,
    *,
    goal: str = "promote",
    mode: str = "sim",
    golden_package_dir: Path | str | None = None,
    perf_baseline_dir: Path | str | None = None,
    policy_path: Path | str | None = None,
) -> dict[str, Any]:
    report = verify_package(
        package_dir,
        goal=goal,
        mode=mode,
        golden_package_dir=golden_package_dir,
        perf_baseline_dir=perf_baseline_dir,
        policy_path=policy_path,
    )
    return report["promotion"]


def policy_check(
    changed_files: list[str] | tuple[str, ...],
    *,
    policy_path: Path | str | None = None,
) -> dict[str, Any]:
    """Evaluate a changed-file set against the configured agent workflow policy."""
    policy = load_agent_policy(policy_path)
    evaluation = evaluate_edit_policy(changed_files, policy)
    return {
        "ok": evaluation["ok"],
        "policy": policy,
        "evaluation": evaluation,
    }


def workflow_state(
    repo_root: Path | str = ".",
    *,
    policy_path: Path | str | None = None,
) -> dict[str, Any]:
    """Summarize the local repository workflow state and active policy obligations."""
    root = Path(repo_root)
    resolved_policy_path = Path(policy_path) if policy_path is not None else root / "agent_policy.toml"
    policy = load_agent_policy(resolved_policy_path)
    branch = _git_output(["git", "branch", "--show-current"], cwd=root).strip()
    changed_files = _git_lines(["git", "status", "--short"], cwd=root)
    changed_paths = [line.split(maxsplit=1)[1] for line in changed_files if len(line.split(maxsplit=1)) == 2]
    task_files = sorted(
        path.name
        for path in (root / "docs" / "in_progress").glob("*.md")
        if path.name != "README.md" and path.name != "TEMPLATE.md"
    )
    base_changed = _git_lines(["git", "diff", "--name-only", "origin/htp/dev...HEAD"], cwd=root)
    policy_evaluation = evaluate_edit_policy(base_changed, policy)
    return {
        "branch": branch,
        "dirty_files": changed_paths,
        "active_task_files": task_files,
        "todo_sync_required": _todo_sync_required(base_changed),
        "policy_check": policy_evaluation,
    }


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
            "promotion_bundle": dict(report.get("promotion_bundle", {})),
            "promotion": dict(report.get("promotion", {})),
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


def _stage_semantic_relpath(manifest: dict[str, Any], stage_id: str, semantic_key: str) -> str:
    stage = next(stage for stage in manifest["stages"]["graph"] if stage["id"] == stage_id)
    semantic = stage.get("semantic", {})
    if isinstance(semantic, dict):
        relpath = semantic.get(semantic_key)
        if isinstance(relpath, str):
            return relpath
    return f"ir/stages/{stage_id}/{semantic_key}.json"


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


def promotion_plan_from_report(report: dict[str, Any]) -> dict[str, Any]:
    bundle = report.get("promotion_bundle", {})
    failed_required = list(bundle.get("failed_required_gates", ()))
    mode = str(bundle.get("mode", report.get("policy", {}).get("agent", {}).get("promotion_mode", "pr")))
    allowed = bool(bundle.get("allowed", False))
    return {
        "mode": mode,
        "allowed": allowed,
        "failed_required_gates": failed_required,
        "next_action": mode if allowed else "hold",
        "reason": "all_required_gates_passed" if allowed else "required_gates_failed",
    }


def _promotion_bundle(report: dict[str, Any]) -> dict[str, Any]:
    policy = report.get("policy", {})
    agent_policy = policy.get("agent", {}) if isinstance(policy, dict) else {}
    required_gates = tuple(str(item) for item in agent_policy.get("required_gates", ()))
    gates = report.get("gates", {})
    failed_required = [gate for gate in required_gates if not bool(gates.get(gate))]
    return {
        "mode": str(agent_policy.get("promotion_mode", "pr")),
        "required_gates": list(required_gates),
        "passed_required_gates": [gate for gate in required_gates if gate not in failed_required],
        "failed_required_gates": failed_required,
        "optional_gates": sorted(key for key in gates if key not in required_gates),
        "allowed": not failed_required and bool(report.get("ok")),
    }


def _write_workflow_report(package_dir: Path, report: dict[str, Any]) -> str:
    agent_dir = package_dir / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    relpath = "agent/workflow_report.json"
    payload = {
        "schema": "htp.agent.workflow_report.v1",
        "gates": dict(report.get("gates", {})),
        "promotion_bundle": dict(report.get("promotion_bundle", {})),
        "promotion": dict(report.get("promotion", {})),
    }
    (package_dir / relpath).write_text(json.dumps(payload, indent=2) + "\n")
    return relpath


def _git_output(cmd: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout


def _git_lines(cmd: list[str], *, cwd: Path) -> list[str]:
    try:
        output = _git_output(cmd, cwd=cwd)
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _todo_sync_required(changed_files: list[str]) -> bool:
    prefixes = ("htp/", "htp_ext/", "examples/", "docs/design/")
    return any(path.startswith(prefix) for path in changed_files for prefix in prefixes)


def _identity_aware_stage_diff(
    left_root: Path,
    right_root: Path,
    left_manifest: dict[str, Any],
    right_manifest: dict[str, Any],
    left_stage_id: str,
    right_stage_id: str,
) -> dict[str, Any]:
    left_stage = next(stage for stage in left_manifest["stages"]["graph"] if stage["id"] == left_stage_id)
    right_stage = next(stage for stage in right_manifest["stages"]["graph"] if stage["id"] == right_stage_id)
    left_entities = _load_stage_json(left_root, left_stage.get("ids", {}).get("entities"))
    right_entities = _load_stage_json(right_root, right_stage.get("ids", {}).get("entities"))
    left_bindings = _load_stage_json(left_root, left_stage.get("ids", {}).get("bindings"))
    right_bindings = _load_stage_json(right_root, right_stage.get("ids", {}).get("bindings"))
    left_entity_map = _load_stage_json(left_root, left_stage.get("maps", {}).get("entity_map"))
    right_entity_map = _load_stage_json(right_root, right_stage.get("maps", {}).get("entity_map"))
    left_binding_map = _load_stage_json(left_root, left_stage.get("maps", {}).get("binding_map"))
    right_binding_map = _load_stage_json(right_root, right_stage.get("maps", {}).get("binding_map"))
    details = {
        "entities": _id_delta(
            [
                item["entity_id"]
                for item in left_entities.get("entities", ())
                if isinstance(item, dict) and "entity_id" in item
            ],
            [
                item["entity_id"]
                for item in right_entities.get("entities", ())
                if isinstance(item, dict) and "entity_id" in item
            ],
        ),
        "bindings": _id_delta(
            [
                item["binding_id"]
                for item in left_bindings.get("bindings", ())
                if isinstance(item, dict) and "binding_id" in item
            ],
            [
                item["binding_id"]
                for item in right_bindings.get("bindings", ())
                if isinstance(item, dict) and "binding_id" in item
            ],
        ),
        "entity_blame": {
            "left_removed": _entity_blame(left_entities, "removed", left_entities, right_entities),
            "right_added": _entity_blame(right_entities, "added", left_entities, right_entities),
        },
        "binding_blame": {
            "left_removed": _binding_blame(left_bindings, "removed", left_bindings, right_bindings),
            "right_added": _binding_blame(right_bindings, "added", left_bindings, right_bindings),
        },
        "entity_map": _summarize_difference(left_entity_map, right_entity_map),
        "binding_map": _summarize_difference(left_binding_map, right_binding_map),
        "refs": {
            "left": {
                "entities": left_stage.get("ids", {}).get("entities"),
                "bindings": left_stage.get("ids", {}).get("bindings"),
                "entity_map": left_stage.get("maps", {}).get("entity_map"),
                "binding_map": left_stage.get("maps", {}).get("binding_map"),
            },
            "right": {
                "entities": right_stage.get("ids", {}).get("entities"),
                "bindings": right_stage.get("ids", {}).get("bindings"),
                "entity_map": right_stage.get("maps", {}).get("entity_map"),
                "binding_map": right_stage.get("maps", {}).get("binding_map"),
            },
        },
    }
    equal = all(
        item
        in (
            {},
            {"kind": "mapping", "added_keys": [], "removed_keys": [], "changed_keys": []},
            {"added": [], "removed": []},
            {"left_removed": [], "right_added": []},
        )
        for key, item in details.items()
        if key != "refs"
    )
    return {"equal": equal, "details": details}


def _replay_stub_diff(
    left_root: Path,
    right_root: Path,
    left_manifest: dict[str, Any],
    right_manifest: dict[str, Any],
    left_stage_id: str,
    right_stage_id: str,
) -> dict[str, Any]:
    left_stage = next(stage for stage in left_manifest["stages"]["graph"] if stage["id"] == left_stage_id)
    right_stage = next(stage for stage in right_manifest["stages"]["graph"] if stage["id"] == right_stage_id)
    left_relpath = _stage_stub_relpath(left_stage)
    right_relpath = _stage_stub_relpath(right_stage)
    left_payload = _load_stage_json(left_root, left_relpath)
    right_payload = _load_stage_json(right_root, right_relpath)
    details = {
        "delta": _summarize_difference(left_payload, right_payload),
        "refs": {
            "left": left_relpath,
            "right": right_relpath,
        },
    }
    equal = details["delta"] in (
        {},
        {"kind": "mapping", "added_keys": [], "removed_keys": [], "changed_keys": []},
    )
    return {"equal": equal, "details": details}


def _pass_trace_diff(left_root: Path, right_root: Path) -> dict[str, Any]:
    left_relpath = "ir/pass_trace.jsonl"
    right_relpath = "ir/pass_trace.jsonl"
    left_payload = _load_jsonl(left_root / left_relpath)
    right_payload = _load_jsonl(right_root / right_relpath)
    details = {
        "delta": _summarize_difference(left_payload, right_payload),
        "refs": {
            "left": left_relpath,
            "right": right_relpath,
        },
    }
    equal = left_payload == right_payload
    return {"equal": equal, "details": details}


def _id_delta(left_ids: list[str], right_ids: list[str]) -> dict[str, Any]:
    left_set = set(left_ids)
    right_set = set(right_ids)
    return {
        "added": sorted(right_set - left_set),
        "removed": sorted(left_set - right_set),
    }


def _entity_blame(
    payload: dict[str, Any],
    direction: str,
    left_entities: dict[str, Any],
    right_entities: dict[str, Any],
) -> list[dict[str, Any]]:
    delta = _id_delta(
        [
            item["entity_id"]
            for item in left_entities.get("entities", ())
            if isinstance(item, dict) and "entity_id" in item
        ],
        [
            item["entity_id"]
            for item in right_entities.get("entities", ())
            if isinstance(item, dict) and "entity_id" in item
        ],
    )
    entity_ids = delta["removed"] if direction == "removed" else delta["added"]
    node_links = {}
    for item in payload.get("node_to_entity", ()):
        if isinstance(item, dict) and "entity_id" in item and "node_id" in item:
            node_links.setdefault(str(item["entity_id"]), []).append(str(item["node_id"]))
    entity_kinds = {
        str(item["entity_id"]): {
            "kind": str(item.get("kind", "")),
            "role": item.get("role"),
        }
        for item in payload.get("entities", ())
        if isinstance(item, dict) and "entity_id" in item
    }
    return [
        {
            "entity_id": entity_id,
            "node_ids": sorted(node_links.get(entity_id, ())),
            **entity_kinds.get(entity_id, {}),
        }
        for entity_id in entity_ids
    ]


def _binding_blame(
    payload: dict[str, Any],
    direction: str,
    left_bindings: dict[str, Any],
    right_bindings: dict[str, Any],
) -> list[dict[str, Any]]:
    delta = _id_delta(
        [
            item["binding_id"]
            for item in left_bindings.get("bindings", ())
            if isinstance(item, dict) and "binding_id" in item
        ],
        [
            item["binding_id"]
            for item in right_bindings.get("bindings", ())
            if isinstance(item, dict) and "binding_id" in item
        ],
    )
    binding_ids = delta["removed"] if direction == "removed" else delta["added"]
    uses_by_binding = {}
    for item in payload.get("name_uses", ()):
        if isinstance(item, dict) and "binding_id" in item and "node_id" in item:
            uses_by_binding.setdefault(str(item["binding_id"]), []).append(str(item["node_id"]))
    records = {
        str(item["binding_id"]): {
            "name": str(item.get("name", "")),
            "site_entity_id": item.get("site_entity_id"),
        }
        for item in payload.get("bindings", ())
        if isinstance(item, dict) and "binding_id" in item
    }
    return [
        {
            "binding_id": binding_id,
            "name_uses": sorted(uses_by_binding.get(binding_id, ())),
            **records.get(binding_id, {}),
        }
        for binding_id in binding_ids
    ]


def _load_stage_json(root: Path, relpath: Any) -> dict[str, Any]:
    if isinstance(relpath, str) and (root / relpath).exists():
        return json.loads((root / relpath).read_text())
    return {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _stage_stub_relpath(stage: dict[str, Any]) -> str | None:
    runnable_py = stage.get("runnable_py", {})
    if isinstance(runnable_py, dict):
        stubs = runnable_py.get("stubs")
        if isinstance(stubs, str):
            return stubs
    return None


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
    "promotion_plan",
    "replay_package",
    "semantic_diff",
    "verify_package",
]
