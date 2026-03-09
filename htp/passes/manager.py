from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import AnalysisSpec, RunnablePySpec, StageSpec, write_stage
from htp.passes.contracts import PassContract
from htp.passes.trace import build_pass_trace_event, emit_pass_trace_event
from htp.schemas import BINDING_MAP_SCHEMA_ID, ENTITY_MAP_SCHEMA_ID


@dataclass(frozen=True)
class PassResult:
    runnable_py: RunnablePySpec
    analyses: dict[str, dict[str, Any]] = field(default_factory=dict)
    islands: tuple[dict[str, str], ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()
    program_ast_payload: dict[str, Any] = field(default_factory=dict)
    kernel_ir_payload: dict[str, Any] = field(default_factory=dict)
    workload_ir_payload: dict[str, Any] = field(default_factory=dict)
    types_payload: dict[str, Any] = field(default_factory=dict)
    layout_payload: dict[str, Any] = field(default_factory=dict)
    effects_payload: dict[str, Any] = field(default_factory=dict)
    schedule_payload: dict[str, Any] = field(default_factory=dict)
    entities_payload: dict[str, Any] = field(default_factory=dict)
    bindings_payload: dict[str, Any] = field(default_factory=dict)
    entity_map_payload: dict[str, Any] | None = None
    binding_map_payload: dict[str, Any] | None = None
    summary_payload: dict[str, Any] | None = None
    digests: dict[str, str | None] = field(default_factory=dict)
    stage_files: tuple[StageFile, ...] = ()
    time_ms: float = 0.0


@dataclass(frozen=True)
class StageFile:
    path: str
    text: str | None = None
    payload: dict[str, Any] | None = None


class PassManager:
    def __init__(
        self,
        *,
        package_dir: Path,
        stages: list[dict[str, object]] | tuple[dict[str, object], ...],
        current_stage: str,
    ) -> None:
        self.package_dir = Path(package_dir)
        self.stages = list(stages)
        self.current_stage = current_stage

    def run(
        self,
        contract: PassContract,
        execute: Callable[[dict[str, object]], PassResult],
        *,
        requires_satisfied: dict[str, Any] | None = None,
        state_delta: dict[str, list[str]] | None = None,
    ) -> dict[str, object]:
        stage_before = self._current_stage_record()
        stage_after_id = self._next_stage_id()
        result = execute(stage_before)
        self._validate_runnable_py(contract=contract, result=result)
        self._validate_analysis_results(contract=contract, result=result)

        self._validate_stage_files(result=result)
        islands = tuple(self._normalize_island(stage_after_id, island) for island in result.islands)

        analyses = tuple(
            AnalysisSpec(
                analysis_id=output.analysis_id,
                schema=output.schema,
                filename=self._analysis_filename(output.path_hint),
                payload=result.analyses[output.path_hint],
            )
            for output in contract.analysis_produces
        )
        stage_record = write_stage(
            self.package_dir,
            StageSpec(
                stage_id=stage_after_id,
                pass_id=contract.pass_id,
                runnable_py=result.runnable_py,
                analyses=analyses,
                islands=islands,
                program_ast_payload=result.program_ast_payload,
                kernel_ir_payload=result.kernel_ir_payload,
                workload_ir_payload=result.workload_ir_payload,
                types_payload=result.types_payload,
                layout_payload=result.layout_payload,
                effects_payload=result.effects_payload,
                schedule_payload=result.schedule_payload,
                entities_payload=result.entities_payload,
                bindings_payload=result.bindings_payload,
                entity_map_payload=self._normalize_map_payload(
                    payload=result.entity_map_payload,
                    schema=ENTITY_MAP_SCHEMA_ID,
                    stage_before=str(stage_before["id"]),
                    stage_after=stage_after_id,
                    pass_id=contract.pass_id,
                    field_name="entities",
                ),
                binding_map_payload=self._normalize_map_payload(
                    payload=result.binding_map_payload,
                    schema=BINDING_MAP_SCHEMA_ID,
                    stage_before=str(stage_before["id"]),
                    stage_after=stage_after_id,
                    pass_id=contract.pass_id,
                    field_name="bindings",
                ),
                summary_payload=result.summary_payload,
                digests=result.digests,
            ),
        )

        self._write_stage_files(stage_after_id=stage_after_id, stage_files=result.stage_files)
        self.stages.append(stage_record)
        self.current_stage = stage_after_id
        write_manifest(self.package_dir, current_stage=self.current_stage, stages=self.stages)

        event = build_pass_trace_event(
            contract=contract,
            stage_before=str(stage_before["id"]),
            stage_after_record=stage_record,
            time_ms=result.time_ms,
            analysis_outputs=tuple(
                {
                    "analysis_id": analysis.analysis_id,
                    "schema": analysis.schema,
                    "path": f"ir/stages/{stage_after_id}/analysis/{analysis.filename}",
                }
                for analysis in analyses
            ),
            diagnostics=result.diagnostics,
            requires_satisfied=requires_satisfied,
            state_delta=state_delta,
        )
        emit_pass_trace_event(self.package_dir, event)
        return stage_record

    def _current_stage_record(self) -> dict[str, object]:
        for stage in self.stages:
            if stage["id"] == self.current_stage:
                return stage
        raise ValueError(f"Unknown current stage: {self.current_stage}")

    def _next_stage_id(self) -> str:
        numeric_ids = [
            int(str(stage["id"])[1:])
            for stage in self.stages
            if str(stage["id"]).startswith("s") and str(stage["id"])[1:].isdigit()
        ]
        next_index = (max(numeric_ids) + 1) if numeric_ids else len(self.stages)
        return f"s{next_index:02d}"

    def _analysis_filename(self, path_hint: str) -> str:
        return PurePosixPath(path_hint).name

    def _normalize_island(self, stage_id: str, island: dict[str, str]) -> dict[str, str]:
        island_id = island.get("island_id")
        island_dir = island.get("dir")
        if not island_id or not island_dir:
            raise ValueError("Island records require island_id and dir")
        path = PurePosixPath(island_dir)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Island dir must be stage-relative")
        if len(path.parts) >= 3 and path.parts[:3] == ("ir", "stages", stage_id):
            return {
                "island_id": island_id,
                "dir": path.as_posix(),
            }
        return {
            "island_id": island_id,
            "dir": f"ir/stages/{stage_id}/{path.as_posix()}",
        }

    def _validate_analysis_results(self, *, contract: PassContract, result: PassResult) -> None:
        expected = {output.path_hint for output in contract.analysis_produces}
        actual = set(result.analyses)

        missing = sorted(expected - actual)
        if missing:
            raise ValueError(f"Missing analysis result for declared output(s): {', '.join(missing)}")

        extra = sorted(actual - expected)
        if extra:
            raise ValueError(f"Undeclared analysis result(s): {', '.join(extra)}")

    def _validate_runnable_py(self, *, contract: PassContract, result: PassResult) -> None:
        expected = contract.runnable_py
        actual = result.runnable_py

        if actual.status != expected.status or tuple(actual.modes) != tuple(expected.modes):
            raise ValueError(
                "Pass result runnable_py does not match contract: "
                f"expected {expected.status}/{expected.modes}, got {actual.status}/{actual.modes}"
            )

    def _validate_stage_files(self, *, result: PassResult) -> None:
        seen: set[str] = set()
        for item in result.stage_files:
            path = PurePosixPath(item.path)
            if (
                not item.path
                or path.is_absolute()
                or ".." in path.parts
                or item.path in seen
                or (item.text is None and item.payload is None)
                or (item.text is not None and item.payload is not None)
            ):
                raise ValueError(f"Invalid stage file declaration: {item.path!r}")
            seen.add(item.path)

    def _write_stage_files(self, *, stage_after_id: str, stage_files: tuple[StageFile, ...]) -> None:
        stage_dir = self.package_dir / "ir" / "stages" / stage_after_id
        for item in stage_files:
            destination = stage_dir / item.path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if item.text is not None:
                destination.write_text(item.text)
            else:
                destination.write_text(json.dumps(item.payload, indent=2) + "\n")

    def _normalize_map_payload(
        self,
        *,
        payload: dict[str, Any] | None,
        schema: str,
        stage_before: str,
        stage_after: str,
        pass_id: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        if payload is None:
            return None
        normalized = dict(payload)
        payload_schema = normalized.get("schema")
        if payload_schema is not None and payload_schema != schema:
            raise ValueError(f"Unexpected map schema: {payload_schema!r} != {schema!r}")
        normalized["schema"] = schema
        normalized.setdefault(field_name, [])
        normalized["pass_id"] = pass_id
        normalized["stage_before"] = stage_before
        normalized["stage_after"] = stage_after
        return normalized


__all__ = ["PassManager", "PassResult", "RunnablePySpec", "StageFile"]
