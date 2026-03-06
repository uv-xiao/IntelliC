from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import AnalysisSpec, RunnablePySpec, StageSpec, write_stage
from htp.passes.contracts import PassContract
from htp.passes.trace import build_pass_trace_event, emit_pass_trace_event


@dataclass(frozen=True)
class PassResult:
    runnable_py: RunnablePySpec
    analyses: dict[str, dict[str, Any]] = field(default_factory=dict)
    diagnostics: tuple[dict[str, Any], ...] = ()
    entities_payload: dict[str, Any] = field(default_factory=dict)
    bindings_payload: dict[str, Any] = field(default_factory=dict)
    entity_map_payload: dict[str, Any] | None = None
    binding_map_payload: dict[str, Any] | None = None
    summary_payload: dict[str, Any] | None = None
    digests: dict[str, str | None] = field(default_factory=dict)
    time_ms: float = 0.0


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
    ) -> dict[str, object]:
        stage_before = self._current_stage_record()
        stage_after_id = self._next_stage_id()
        result = execute(stage_before)

        analyses = tuple(
            AnalysisSpec(
                analysis_id=output.analysis_id,
                schema=output.schema,
                filename=self._analysis_filename(output.path_hint),
                payload=result.analyses.get(output.path_hint, {}),
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
                entities_payload=result.entities_payload,
                bindings_payload=result.bindings_payload,
                entity_map_payload=result.entity_map_payload,
                binding_map_payload=result.binding_map_payload,
                summary_payload=result.summary_payload,
                digests=result.digests,
            ),
        )

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
        path = PurePosixPath(path_hint)
        if path.parts and path.parts[0] == "analysis":
            return path.name
        return path.as_posix()


__all__ = ["PassManager", "PassResult", "RunnablePySpec"]
