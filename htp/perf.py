from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_perf_payload(package_dir: Path | str) -> dict[str, Any] | None:
    root = Path(package_dir)
    candidate_paths = (
        root / "metrics" / "perf.json",
        root / "build" / "perf.json",
    )
    for path in candidate_paths:
        if path.is_file():
            payload = json.loads(path.read_text())
            if isinstance(payload, dict):
                return payload
    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        extensions = manifest.get("extensions", {})
        perf_payload = extensions.get("perf") if isinstance(extensions, dict) else None
        if isinstance(perf_payload, dict):
            return perf_payload
    return None


def compare_perf(
    current: dict[str, Any] | None,
    baseline: dict[str, Any] | None,
    *,
    max_regression_pct: float,
) -> dict[str, Any]:
    if current is None:
        return {
            "ok": False,
            "reason": "missing_current_metrics",
        }
    if baseline is None:
        return {
            "ok": False,
            "reason": "missing_baseline_metrics",
        }
    current_metric = _coerce_metric(current.get("runtime_ms"))
    baseline_metric = _coerce_metric(baseline.get("runtime_ms"))
    if current_metric is None or baseline_metric is None:
        return {
            "ok": False,
            "reason": "missing_runtime_ms",
            "current": current,
            "baseline": baseline,
        }
    regression_pct = (
        ((current_metric - baseline_metric) / baseline_metric) * 100.0 if baseline_metric else 0.0
    )
    return {
        "ok": regression_pct <= max_regression_pct,
        "metric": "runtime_ms",
        "current": current_metric,
        "baseline": baseline_metric,
        "regression_pct": regression_pct,
        "threshold_pct": max_regression_pct,
    }


def _coerce_metric(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


__all__ = ["compare_perf", "load_perf_payload"]
