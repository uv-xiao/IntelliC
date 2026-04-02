from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from htp.passes.contracts import PassContract

PASS_TRACE_EVENT_SCHEMA_ID = "htp.pass_trace_event.v1"
_EMPTY_STATE_DELTA = {
    "provides": [],
    "invalidates": [],
    "preserved_capabilities": [],
    "added_analyses": [],
    "removed_analyses": [],
    "preserved_analyses": [],
    "added_layout_invariants": [],
    "removed_layout_invariants": [],
    "preserved_layout_invariants": [],
    "added_effect_invariants": [],
    "removed_effect_invariants": [],
    "preserved_effect_invariants": [],
}


@dataclass(frozen=True)
class PassTraceEvent:
    pass_id: str
    kind: str
    ast_effect: str
    stage_before: str
    stage_after: str
    time_ms: float
    requires: tuple[str, ...]
    requires_satisfied: dict[str, Any]
    cap_delta: dict[str, list[str]]
    analysis: dict[str, Any]
    runnable_py: dict[str, Any]
    dumps: dict[str, Any]
    maps: dict[str, Any]
    diagnostics: tuple[dict[str, Any], ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": PASS_TRACE_EVENT_SCHEMA_ID,
            "pass_id": self.pass_id,
            "kind": self.kind,
            "ast_effect": self.ast_effect,
            "stage_before": self.stage_before,
            "stage_after": self.stage_after,
            "time_ms": self.time_ms,
            "requires": list(self.requires),
            "requires_satisfied": dict(self.requires_satisfied),
            "cap_delta": {
                "provides": list(self.cap_delta.get("provides", [])),
                "invalidates": list(self.cap_delta.get("invalidates", [])),
                "preserved_capabilities": list(self.cap_delta.get("preserved_capabilities", [])),
                "added_analyses": list(self.cap_delta.get("added_analyses", [])),
                "removed_analyses": list(self.cap_delta.get("removed_analyses", [])),
                "preserved_analyses": list(self.cap_delta.get("preserved_analyses", [])),
                "added_layout_invariants": list(self.cap_delta.get("added_layout_invariants", [])),
                "removed_layout_invariants": list(self.cap_delta.get("removed_layout_invariants", [])),
                "preserved_layout_invariants": list(self.cap_delta.get("preserved_layout_invariants", [])),
                "added_effect_invariants": list(self.cap_delta.get("added_effect_invariants", [])),
                "removed_effect_invariants": list(self.cap_delta.get("removed_effect_invariants", [])),
                "preserved_effect_invariants": list(self.cap_delta.get("preserved_effect_invariants", [])),
            },
            "analysis": {
                "requires": list(self.analysis.get("requires", [])),
                "produces": list(self.analysis.get("produces", [])),
            },
            "runnable_py": dict(self.runnable_py),
            "dumps": {
                "program": self.dumps.get("program"),
                "stage": self.dumps.get("stage"),
                "state": self.dumps.get("state"),
                "stubs": self.dumps.get("stubs"),
            },
            "maps": dict(self.maps),
            "diagnostics": list(self.diagnostics),
        }


def build_pass_trace_event(
    *,
    contract: PassContract,
    stage_before: str,
    stage_after_record: dict[str, Any],
    time_ms: float,
    analysis_outputs: tuple[dict[str, str], ...],
    diagnostics: tuple[dict[str, Any], ...] = (),
    requires_satisfied: dict[str, Any] | None = None,
    state_delta: dict[str, list[str]] | None = None,
) -> PassTraceEvent:
    state_path = str(stage_after_record["state"])
    maps_payload = {}
    rewrite_maps = stage_after_record.get("rewrite_maps", {})
    if state_path and isinstance(rewrite_maps, dict):
        if rewrite_maps.get("entity_map"):
            maps_payload["entity_map"] = f"{state_path}#/identity/entity_map"
        if rewrite_maps.get("binding_map"):
            maps_payload["binding_map"] = f"{state_path}#/identity/binding_map"
    elif state_path:
        maps_payload = {
            "entity_map": f"{state_path}#/identity/entity_map",
            "binding_map": f"{state_path}#/identity/binding_map",
        }
    return PassTraceEvent(
        pass_id=contract.pass_id,
        kind=contract.kind,
        ast_effect=contract.ast_effect,
        stage_before=stage_before,
        stage_after=str(stage_after_record["id"]),
        time_ms=time_ms,
        requires=contract.requires,
        requires_satisfied=requires_satisfied or {},
        cap_delta={
            "provides": list((state_delta or {}).get("provides", contract.provides)),
            "invalidates": list((state_delta or {}).get("invalidates", contract.invalidates)),
            **{
                key: list((state_delta or _EMPTY_STATE_DELTA).get(key, default))
                for key, default in _EMPTY_STATE_DELTA.items()
                if key not in {"provides", "invalidates"}
            },
        },
        analysis={
            "requires": list(contract.analysis_requires),
            "produces": list(analysis_outputs),
        },
        runnable_py={
            "status": stage_after_record["runnable_py"]["status"],
            "modes": list(stage_after_record["runnable_py"]["modes"]),
            "program_py": stage_after_record["runnable_py"]["program_py"],
            "preserves_python_renderability": contract.runnable_py.preserves_python_renderability,
            "preserves_python_executability": contract.runnable_py.preserves_python_executability,
        },
        dumps={
            "program": stage_after_record["program"],
            "stage": stage_after_record["stage"],
            "state": stage_after_record["state"],
            "stubs": stage_after_record["runnable_py"]["stubs"],
        },
        maps=maps_payload,
        diagnostics=tuple(diagnostics),
    )


def emit_pass_trace_event(package_dir: Path, event: PassTraceEvent) -> None:
    trace_path = Path(package_dir) / "ir" / "pass_trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_json()) + "\n")


__all__ = [
    "PASS_TRACE_EVENT_SCHEMA_ID",
    "PassTraceEvent",
    "build_pass_trace_event",
    "emit_pass_trace_event",
]
