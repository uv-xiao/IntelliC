from __future__ import annotations

import importlib.util
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from htp.runtime.errors import ReplayDiagnosticError

from .validate import CONTRACT_REFS, collect_missing_files, manifest_target, validation_diagnostics

Diagnostic = dict[str, Any]


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
        stage_id = self._resolve_current_stage_id()
        ok, result, diagnostics = self._execute_entry(
            kind="run",
            stage_id=stage_id,
            entry_name=entry,
            args=args,
            kwargs=kwargs,
            mode=self.mode,
            trace=trace,
        )
        log_path = self._write_operation_log(
            kind="run",
            mode=self.mode,
            stage_id=stage_id,
            entry=entry,
            trace=trace,
            ok=ok,
            diagnostics=diagnostics,
        )
        return RunResult(
            ok=ok,
            mode=self.mode,
            entry=entry,
            result=result,
            diagnostics=diagnostics,
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
        ok, result, diagnostics = self._execute_entry(
            kind="replay",
            stage_id=stage_id,
            entry_name=entry_name,
            args=args,
            kwargs=kwargs,
            mode=replay_mode,
            trace=trace,
        )
        log_path = self._write_operation_log(
            kind="replay",
            mode=replay_mode,
            stage_id=stage_id,
            entry=entry_name,
            trace=trace,
            ok=ok,
            diagnostics=diagnostics,
        )
        return ReplayResult(
            ok=ok,
            mode=replay_mode,
            entry=entry_name,
            stage_id=stage_id,
            result=result,
            diagnostics=diagnostics,
            log_path=log_path,
        )

    def _current_stage_id(self) -> str:
        stages = self.manifest.get("stages", {})
        return str(stages["current"])

    def _stage_record(self, stage_id: str) -> dict[str, Any]:
        stages = self.manifest.get("stages", {})
        if not isinstance(stages, Mapping):
            raise ValueError("Manifest stages must be a mapping with a graph list.")
        graph = stages.get("graph", ())
        if not isinstance(graph, list):
            raise ValueError("Manifest stages.graph must be a list.")
        for stage in graph:
            if not isinstance(stage, Mapping):
                raise ValueError("Manifest stages.graph entries must be mappings.")
            if stage.get("id") == stage_id:
                return dict(stage)
        raise KeyError(f"Unknown stage id: {stage_id}")

    def _write_log(self, *, kind: str, stem: str, lines: tuple[str, ...]) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        relative_path = Path("logs") / f"{stem}_{timestamp}_{uuid4().hex[:8]}.log"
        log_path = self.package_dir / relative_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = "\n".join((f"kind={kind}", *lines)) + "\n"
        log_path.write_text(payload)
        return relative_path.as_posix()

    def _resolve_current_stage_id(self) -> str:
        try:
            return self._current_stage_id()
        except Exception:
            return "<unknown>"

    def _execute_entry(
        self,
        *,
        kind: str,
        stage_id: str,
        entry_name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any] | None,
        mode: str,
        trace: str,
    ) -> tuple[bool, Any, list[Diagnostic]]:
        try:
            stage = self._stage_record(stage_id)
        except KeyError:
            return (
                False,
                None,
                [
                    {
                        "code": "HTP.BINDINGS.STAGE_NOT_FOUND",
                        "detail": f"Unknown stage id: {stage_id}",
                        "stage_id": stage_id,
                    }
                ],
            )
        except ValueError as exc:
            return (
                False,
                None,
                [
                    {
                        "code": "HTP.BINDINGS.MALFORMED_STAGE_GRAPH",
                        "detail": str(exc),
                        "stage_id": stage_id,
                    }
                ],
            )

        runnable_py = stage.get("runnable_py", {})
        if not isinstance(runnable_py, Mapping):
            return (
                False,
                None,
                [
                    {
                        "code": "HTP.BINDINGS.MALFORMED_RUNNABLE_PY",
                        "detail": f"Stage {stage_id!r} has a non-mapping runnable_py record.",
                        "stage_id": stage_id,
                    }
                ],
            )
        modes_value = runnable_py.get("modes", ())
        if (
            modes_value is None
            or isinstance(modes_value, (str, bytes))
            or not isinstance(modes_value, Iterable)
        ):
            return (
                False,
                None,
                [
                    {
                        "code": "HTP.BINDINGS.MALFORMED_RUNNABLE_MODES",
                        "detail": f"Stage {stage_id!r} has a non-iterable runnable_py.modes value.",
                        "stage_id": stage_id,
                    }
                ],
            )
        supported_modes = tuple(modes_value)
        if supported_modes and mode not in supported_modes:
            return (
                False,
                None,
                [
                    {
                        "code": "HTP.BINDINGS.UNSUPPORTED_REPLAY_MODE",
                        "detail": f"Stage {stage_id!r} does not support replay mode {mode!r}.",
                        "stage_id": stage_id,
                    }
                ],
            )

        program_relpath = runnable_py.get("program_py")
        if not isinstance(program_relpath, str):
            return (
                False,
                None,
                [
                    {
                        "code": f"HTP.BINDINGS.{kind.upper()}_LOAD_ERROR",
                        "detail": f"Stage {stage_id!r} is missing runnable_py.program_py.",
                        "stage_id": stage_id,
                    }
                ],
            )

        program_path = self.package_dir / program_relpath
        try:
            module = _load_program_module(program_path, stage_id=stage_id)
        except Exception as exc:
            return (
                False,
                None,
                [
                    {
                        "code": f"HTP.BINDINGS.{kind.upper()}_LOAD_ERROR",
                        "detail": str(exc),
                        "stage_id": stage_id,
                        "entry": entry_name,
                        "program_py": program_relpath,
                        "exception_type": exc.__class__.__name__,
                    }
                ],
            )

        if not hasattr(module, entry_name):
            return (
                False,
                None,
                [
                    {
                        "code": "HTP.BINDINGS.MISSING_ENTRYPOINT",
                        "detail": f"Entrypoint {entry_name!r} is not defined for stage {stage_id!r}.",
                        "stage_id": stage_id,
                        "entry": entry_name,
                        "program_py": program_relpath,
                    }
                ],
            )

        try:
            result = getattr(module, entry_name)(*args, **({} if kwargs is None else kwargs))
        except ReplayDiagnosticError as exc:
            diagnostic = dict(exc.payload)
            diagnostic["code"] = exc.code
            if exc.fix_hints:
                diagnostic["fix_hints"] = list(exc.fix_hints)
            return False, None, [diagnostic]
        except Exception as exc:
            return (
                False,
                None,
                [
                    {
                        "code": f"HTP.BINDINGS.{kind.upper()}_EXECUTION_ERROR",
                        "detail": str(exc),
                        "stage_id": stage_id,
                        "entry": entry_name,
                        "program_py": program_relpath,
                        "exception_type": exc.__class__.__name__,
                    }
                ],
            )

        return True, result, []

    def _write_operation_log(
        self,
        *,
        kind: str,
        mode: str,
        stage_id: str,
        entry: str,
        trace: str,
        ok: bool,
        diagnostics: list[Diagnostic],
    ) -> str:
        diagnostic_codes = ",".join(str(diagnostic.get("code", "")) for diagnostic in diagnostics)
        return self._write_log(
            kind=kind,
            stem=f"{kind}_{stage_id}_{mode}" if kind == "replay" else f"{kind}_{self.backend}_{mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={mode}",
                f"stage_id={stage_id}",
                f"entry={entry}",
                f"trace={trace}",
                f"ok={ok}",
                f"diagnostic_codes={diagnostic_codes}",
            ),
        )


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
