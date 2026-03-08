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
            merged_section.update(value)
            merged[section] = merged_section
    return merged


def _clone_default_policy() -> dict[str, Any]:
    return {
        "agent": dict(DEFAULT_POLICY["agent"]),
        "perf": dict(DEFAULT_POLICY["perf"]),
    }


__all__ = ["DEFAULT_POLICY", "load_agent_policy"]
