"""Agent policy loading and workflow-corridor evaluation."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

DEFAULT_POLICY = {
    "agent": {
        "allowed_edit_roots": [
            "htp",
            "htp_ext",
            "tests",
            "docs",
            ".github",
            ".agent",
            "AGENTS.md",
            "README.md",
            "agent_policy.toml",
        ],
        "required_gates": ["validate", "replay"],
        "promotion_mode": "pr",
        "edit_corridors": {
            "passes": ["htp/passes", "tests/passes", "docs/design/pipeline_and_solver.md"],
            "intrinsics": ["htp/intrinsics.py", "htp/runtime/intrinsics.py", "tests/ir"],
            "backends": ["htp/backends", "htp/bindings", "tests/backends", "docs/design"],
        },
        "edit_corridor_templates": {
            "passes": {
                "trigger_roots": ["htp/passes"],
                "allowed_roots": [
                    "htp/passes",
                    "tests/passes",
                    "docs/design/pipeline_and_solver.md",
                ],
                "required_tests": ["tests/passes", "tests/pipeline"],
                "required_docs": [
                    "docs/design/pipeline_and_solver.md",
                    "docs/todo/README.md",
                ],
                "contract_surfaces": ["pass contracts", "analysis payloads", "ir/pass_trace.jsonl"],
            },
            "intrinsics": {
                "trigger_roots": ["htp/intrinsics.py", "htp/runtime/intrinsics.py"],
                "allowed_roots": ["htp/intrinsics.py", "htp/runtime/intrinsics.py", "tests/ir"],
                "required_tests": ["tests/ir", "tests/runtime"],
                "required_docs": [
                    "docs/design/compiler_model.md",
                    "docs/todo/README.md",
                ],
                "contract_surfaces": ["intrinsic registry", "simulate/lower handlers", "stub diagnostics"],
            },
            "backend_contracts": {
                "trigger_roots": ["htp/backends", "htp/bindings", "htp_ext"],
                "allowed_roots": [
                    "htp/backends",
                    "htp/bindings",
                    "htp_ext",
                    "tests/backends",
                    "tests/bindings",
                    "tests/examples",
                    "docs/design",
                ],
                "required_tests": ["tests/backends", "tests/bindings", "tests/examples"],
                "required_docs": [
                    "docs/design/artifacts_replay_debug.md",
                    "docs/design/backends_and_extensions.md",
                    "docs/todo/README.md",
                ],
                "contract_surfaces": ["manifest.outputs", "backend codegen index", "adapter traces"],
            },
            "agent_workflow": {
                "trigger_roots": [
                    "htp/agent_policy.py",
                    "htp/tools.py",
                    "htp/__main__.py",
                    ".github/scripts/check_pr_policy.py",
                    "agent_policy.toml",
                ],
                "allowed_roots": [
                    "htp/agent_policy.py",
                    "htp/tools.py",
                    "htp/__main__.py",
                    ".github/scripts/check_pr_policy.py",
                    "agent_policy.toml",
                    "tests/tools",
                    "tests/test_pr_policy_script.py",
                    "docs/design/agent_product_and_workflow.md",
                    "docs/todo/README.md",
                    "AGENTS.md",
                    ".agent/rules",
                    "README.md",
                ],
                "required_tests": ["tests/tools", "tests/test_pr_policy_script.py"],
                "required_docs": [
                    "docs/design/agent_product_and_workflow.md",
                    "docs/todo/README.md",
                    "AGENTS.md",
                ],
                "contract_surfaces": [
                    "agent policy",
                    "promotion-gate bundle",
                    "workflow-state inspection",
                    "pr policy enforcement",
                ],
            },
        },
    },
    "perf": {
        "enabled": False,
        "max_regression_pct": 5.0,
    },
}


def load_agent_policy(path: Path | str | None = None) -> dict[str, Any]:
    """Load repository agent policy, merging an optional TOML override over defaults."""
    if path is None:
        default_path = Path("agent_policy.toml")
        if default_path.is_file():
            path = default_path
    if path is None:
        return _clone_default_policy()

    policy_path = Path(path)
    if not policy_path.is_file():
        return _clone_default_policy()

    payload = tomllib.loads(policy_path.read_text())
    merged = _clone_default_policy()
    for section in ("agent", "perf"):
        value = payload.get(section)
        if isinstance(value, dict):
            merged_section = dict(merged[section])
            for key, item in value.items():
                if isinstance(item, dict) and isinstance(merged_section.get(key), dict):
                    nested = dict(merged_section[key])
                    nested.update(item)
                    merged_section[key] = nested
                else:
                    merged_section[key] = item
            merged[section] = merged_section
    return merged


def _clone_default_policy() -> dict[str, Any]:
    return {
        "agent": {
            **dict(DEFAULT_POLICY["agent"]),
            "edit_corridors": {
                key: list(value) for key, value in DEFAULT_POLICY["agent"]["edit_corridors"].items()
            },
            "edit_corridor_templates": {
                key: dict(value) for key, value in DEFAULT_POLICY["agent"]["edit_corridor_templates"].items()
            },
        },
        "perf": dict(DEFAULT_POLICY["perf"]),
    }


def evaluate_edit_policy(
    changed_files: Iterable[str],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate changed files against allowed roots and active edit-corridor templates."""
    active_policy = policy if policy is not None else _clone_default_policy()
    agent_policy = active_policy.get("agent", {}) if isinstance(active_policy, dict) else {}
    allowed_roots = tuple(str(item) for item in agent_policy.get("allowed_edit_roots", ()))
    templates = agent_policy.get("edit_corridor_templates", {})
    paths = [path for path in changed_files if path]

    root_violations = [path for path in paths if not _matches_any_root(path, allowed_roots)]
    active_templates: list[dict[str, Any]] = []
    missing_tests: list[str] = []
    missing_docs: list[str] = []
    contract_surfaces: list[str] = []

    for name, raw_template in templates.items():
        if not isinstance(raw_template, dict):
            continue
        allowed = tuple(str(item) for item in raw_template.get("allowed_roots", ()))
        triggers = tuple(str(item) for item in raw_template.get("trigger_roots", allowed))
        if not any(_matches_any_root(path, triggers) for path in paths):
            continue
        required_tests = [str(item) for item in raw_template.get("required_tests", ())]
        required_docs = [str(item) for item in raw_template.get("required_docs", ())]
        missing_template_tests = [
            item for item in required_tests if not any(_matches_root(path, item) for path in paths)
        ]
        missing_template_docs = [
            item for item in required_docs if not any(_matches_root(path, item) for path in paths)
        ]
        active_templates.append(
            {
                "name": name,
                "allowed_roots": list(allowed),
                "required_tests": required_tests,
                "required_docs": required_docs,
                "missing_required_tests": missing_template_tests,
                "missing_required_docs": missing_template_docs,
                "contract_surfaces": [str(item) for item in raw_template.get("contract_surfaces", ())],
            }
        )
        missing_tests.extend(item for item in missing_template_tests if item not in missing_tests)
        missing_docs.extend(item for item in missing_template_docs if item not in missing_docs)
        for surface in raw_template.get("contract_surfaces", ()):
            if surface not in contract_surfaces:
                contract_surfaces.append(str(surface))

    return {
        "ok": not root_violations and not missing_tests and not missing_docs,
        "changed_files": paths,
        "root_violations": root_violations,
        "active_templates": active_templates,
        "missing_required_tests": missing_tests,
        "missing_required_docs": missing_docs,
        "contract_surfaces": contract_surfaces,
    }


def _matches_any_root(path: str, roots: Iterable[str]) -> bool:
    return any(_matches_root(path, root) for root in roots)


def _matches_root(path: str, root: str) -> bool:
    if not root:
        return False
    return path == root or path.startswith(f"{root}/")


__all__ = ["DEFAULT_POLICY", "evaluate_edit_policy", "load_agent_policy"]
