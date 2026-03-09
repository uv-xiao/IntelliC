from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

DEFAULT_POLICY = {
    "agent": {
        "allowed_edit_roots": ["htp", "htp_ext", "tests", "docs", ".github"],
        "required_gates": ["validate", "replay"],
        "promotion_mode": "pr",
        "edit_corridors": {
            "passes": ["htp/passes", "tests/passes", "docs/design/03_pipeline_and_solver.md"],
            "intrinsics": ["htp/intrinsics.py", "htp/runtime/intrinsics.py", "tests/ir"],
            "backends": ["htp/backends", "htp/bindings", "tests/backends", "docs/design"],
        },
        "edit_corridor_templates": {
            "passes": {
                "allowed_roots": [
                    "htp/passes",
                    "tests/passes",
                    "docs/design/03_pipeline_and_solver.md",
                ],
                "required_tests": ["tests/passes", "tests/pipeline"],
                "required_docs": [
                    "docs/design/03_pipeline_and_solver.md",
                    "docs/todo/README.md",
                    "docs/todo/03_pipeline_and_solver.md",
                ],
                "contract_surfaces": ["pass contracts", "analysis payloads", "ir/pass_trace.jsonl"],
            },
            "intrinsics": {
                "allowed_roots": ["htp/intrinsics.py", "htp/runtime/intrinsics.py", "tests/ir"],
                "required_tests": ["tests/ir", "tests/runtime"],
                "required_docs": [
                    "docs/design/01_compiler_model.md",
                    "docs/todo/README.md",
                    "docs/todo/01_compiler_model.md",
                ],
                "contract_surfaces": ["intrinsic registry", "simulate/lower handlers", "stub diagnostics"],
            },
            "backend_contracts": {
                "allowed_roots": [
                    "htp/backends",
                    "htp/bindings",
                    "tests/backends",
                    "docs/design",
                ],
                "required_tests": ["tests/backends", "tests/bindings", "tests/examples"],
                "required_docs": [
                    "docs/design/04_artifacts_replay_debug.md",
                    "docs/design/05_backends_and_extensions.md",
                    "docs/todo/README.md",
                    "docs/todo/05_backends_and_extensions.md",
                ],
                "contract_surfaces": ["manifest.outputs", "backend codegen index", "adapter traces"],
            },
        },
    },
    "perf": {
        "enabled": False,
        "max_regression_pct": 5.0,
    },
}


def load_agent_policy(path: Path | str | None = None) -> dict[str, Any]:
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


__all__ = ["DEFAULT_POLICY", "load_agent_policy"]
