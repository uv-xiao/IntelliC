from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .validate import CONTRACT_REFS, collect_missing_files, manifest_target, validation_diagnostics


Diagnostic = dict[str, str]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    backend: str
    variant: str | None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    contract_refs: tuple[str, ...] = CONTRACT_REFS


@dataclass(frozen=True)
class BuildResult:
    ok: bool
    mode: str
    built_outputs: list[str] = field(default_factory=list)
    log_paths: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class RunResult:
    ok: bool
    mode: str
    entry: str
    result: Any = None
    result_ref: str | None = None
    trace_ref: str | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    log_path: str | None = None


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    mode: str
    entry: str
    stage_id: str
    result: Any = None
    result_ref: str | None = None
    trace_ref: str | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    log_path: str | None = None


@dataclass(frozen=True)
class LoadResult:
    package_dir: Path
    manifest: dict[str, Any]
    backend: str
    variant: str | None
    mode: str
    diagnostics: list[Diagnostic] = field(default_factory=list)
    ok: bool = True

    def run(
        self,
        entry: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        trace: str = "off",
    ) -> RunResult:
        current_stage = self._current_stage_id()
        replay_result = self.replay(current_stage, entry=entry, args=args, kwargs=kwargs, mode=self.mode, trace=trace)
        log_path = self._write_log(
            kind="run",
            stem=f"run_{self.backend}_{self.mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={self.mode}",
                f"entry={entry}",
                f"stage_id={current_stage}",
                f"ok={replay_result.ok}",
            ),
        )
        return RunResult(
            ok=replay_result.ok,
            mode=self.mode,
            entry=entry,
            result=replay_result.result,
            result_ref=replay_result.result_ref,
            trace_ref=replay_result.trace_ref,
            diagnostics=replay_result.diagnostics,
            log_path=log_path,
        )

    def replay(
        self,
        stage_id: str,
        *,
        entry: str | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        mode: str | None = None,
        trace: str = "basic",
    ) -> ReplayResult:
        replay_mode = self.mode if mode is None else mode
        entry_name = "run" if entry is None else entry
        stage = self._stage_record(stage_id)
        runnable_py = stage.get("runnable_py", {})
        supported_modes = tuple(runnable_py.get("modes", ()))
        diagnostics: list[Diagnostic] = []
        if supported_modes and replay_mode not in supported_modes:
            diagnostics = [
                {
                    "code": "HTP.BINDINGS.UNSUPPORTED_REPLAY_MODE",
                    "detail": f"Stage {stage_id!r} does not support replay mode {replay_mode!r}.",
                }
            ]
            return ReplayResult(
                ok=False,
                mode=replay_mode,
                entry=entry_name,
                stage_id=stage_id,
                diagnostics=diagnostics,
            )

        program_path = self.package_dir / str(runnable_py["program_py"])
        module = _load_program_module(program_path, stage_id=stage_id)
        result = getattr(module, entry_name)(*args, **({} if kwargs is None else kwargs))
        log_path = self._write_log(
            kind="replay",
            stem=f"replay_{stage_id}_{replay_mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={replay_mode}",
                f"stage_id={stage_id}",
                f"entry={entry_name}",
                f"trace={trace}",
                "ok=True",
            ),
        )
        return ReplayResult(
            ok=True,
            mode=replay_mode,
            entry=entry_name,
            stage_id=stage_id,
            result=result,
            diagnostics=[],
            log_path=log_path,
        )

    def _current_stage_id(self) -> str:
        stages = self.manifest.get("stages", {})
        return str(stages["current"])

    def _stage_record(self, stage_id: str) -> dict[str, Any]:
        stages = self.manifest.get("stages", {})
        for stage in stages.get("graph", ()):
            if stage.get("id") == stage_id:
                return stage
        raise KeyError(f"Unknown stage id: {stage_id}")

    def _write_log(self, *, kind: str, stem: str, lines: tuple[str, ...]) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        relative_path = Path("logs") / f"{stem}_{timestamp}.log"
        log_path = self.package_dir / relative_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = "\n".join((f"kind={kind}", *lines)) + "\n"
        log_path.write_text(payload)
        return relative_path.as_posix()


@dataclass(frozen=True)
class ManifestBinding:
    package_dir: Path
    manifest: dict[str, Any]
    backend: str
    variant: str | None

    def validate(self) -> ValidationResult:
        missing_files = list(collect_missing_files(self.package_dir, self.manifest))
        diagnostics = list(validation_diagnostics(self.manifest, tuple(missing_files)))
        return ValidationResult(
            ok=not diagnostics,
            backend=self.backend,
            variant=self.variant,
            diagnostics=diagnostics,
            missing_files=missing_files,
        )

    def build(
        self,
        *,
        mode: str = "sim",
        force: bool = False,
        cache_dir: Path | None = None,
    ) -> BuildResult:
        del force
        del cache_dir
        validation = self.validate()
        session = self.load(mode=mode)
        log_path = session._write_log(
            kind="build",
            stem=f"build_{self.backend}_{mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={mode}",
                f"validated={validation.ok}",
                "built_outputs=()",
            ),
        )
        return BuildResult(
            ok=validation.ok,
            mode=mode,
            built_outputs=[],
            log_paths=[log_path],
            diagnostics=validation.diagnostics,
        )

    def load(self, *, mode: str = "sim") -> LoadResult:
        validation = self.validate()
        return LoadResult(
            package_dir=self.package_dir,
            manifest=self.manifest,
            backend=self.backend,
            variant=self.variant,
            mode=mode,
            diagnostics=validation.diagnostics,
            ok=validation.ok,
        )


def _load_program_module(program_path: Path, *, stage_id: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"htp_stage_{stage_id}", program_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load replay program for stage {stage_id!r} from {program_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def binding_from_manifest(package_dir: Path | str, manifest: dict[str, Any]) -> ManifestBinding:
    backend, variant = manifest_target(manifest)
    if backend is None:
        raise ValueError("Manifest target.backend is required for binding selection")
    return ManifestBinding(
        package_dir=Path(package_dir),
        manifest=manifest,
        backend=backend,
        variant=variant,
    )


BindingSession = LoadResult


__all__ = [
    "BindingSession",
    "BuildResult",
    "LoadResult",
    "ManifestBinding",
    "ReplayResult",
    "RunResult",
    "ValidationResult",
    "binding_from_manifest",
]
