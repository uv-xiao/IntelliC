from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from htp.passes.contracts import PassContract

PASS_TRACE_EVENT_SCHEMA_ID = "htp.pass_trace_event.v1"


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
            },
            "analysis": {
                "requires": list(self.analysis.get("requires", [])),
                "produces": list(self.analysis.get("produces", [])),
            },
            "runnable_py": dict(self.runnable_py),
            "dumps": {
                "program_py": self.dumps.get("program_py"),
                "program_pyast": self.dumps.get("program_pyast"),
                "metadata": dict(self.dumps.get("metadata", {})),
                "ids": dict(self.dumps.get("ids", {})),
                "analysis_index": self.dumps.get("analysis_index"),
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
) -> PassTraceEvent:
    maps_payload = {
        key: value
        for key, value in {
            "entity_map": stage_after_record["maps"]["entity_map"],
            "binding_map": stage_after_record["maps"]["binding_map"],
        }.items()
        if value is not None
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
            "provides": list(contract.provides),
            "invalidates": list(contract.invalidates),
        },
        analysis={
            "requires": list(contract.analysis_requires),
            "produces": list(analysis_outputs),
        },
        runnable_py={
            "status": stage_after_record["runnable_py"]["status"],
            "modes": list(stage_after_record["runnable_py"]["modes"]),
            "program_py": stage_after_record["runnable_py"]["program_py"],
        },
        dumps={
            "program_py": stage_after_record["runnable_py"]["program_py"],
            "program_pyast": None,
            "metadata": {},
            "ids": {
                "entities": stage_after_record["ids"]["entities"],
                "bindings": stage_after_record["ids"]["bindings"],
            },
            "analysis_index": stage_after_record["analysis_index"],
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
