from __future__ import annotations

import importlib
import importlib.util
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from htp.schemas import ADAPTER_TRACE_SCHEMA_ID, PERF_SCHEMA_ID
from htp_ext.cpu_ref.declarations import declaration_for
from htp_ext.cpu_ref.emit import CPU_REF_CODEGEN_SCHEMA_ID, CPU_REF_TOOLCHAIN_SCHEMA_ID

from .base import BuildResult, LoadResult, ManifestBinding, RunResult, ValidationResult

_CPU_REF_OUTPUTS = declaration_for().artifact_contract.as_manifest_outputs()
_REQUIRED_PATHS = (
    "codegen/cpu_ref/reference.py",
    _CPU_REF_OUTPUTS["cpu_ref_codegen_index"],
    _CPU_REF_OUTPUTS["toolchain_manifest"],
)


def build_reference_runtime(package_dir: Path | str, manifest: dict[str, Any] | None = None) -> list[str]:
    package_path = Path(package_dir)
    package_manifest = manifest or json.loads((package_path / "manifest.json").read_text())
    build_dir = package_path / "build" / "cpu_ref"
    build_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "htp.cpu_ref.runtime.v1",
        "entry": package_manifest.get("inputs", {}).get("entry", ""),
        "target": dict(package_manifest.get("target", {})),
        "launch_entry": dict(
            package_manifest.get("extensions", {}).get("cpu_ref", {}).get("launch_entry", {})
        ),
    }
    (build_dir / "runtime.json").write_text(json.dumps(payload, indent=2) + "\n")
    return ["build/cpu_ref/runtime.json"]


class CPURefLoadResult(LoadResult):
    def run(
        self,
        entry: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        trace: str = "off",
    ) -> RunResult:
        stage_id = self._resolve_current_stage_id()
        diagnostics = list(self.diagnostics)
        if kwargs:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.CPU_REF_UNSUPPORTED_KEYWORD_ARGS",
                    "detail": "CPU reference packages currently support positional arguments only.",
                }
            )
        launch_entry = _launch_entry(self.manifest)
        if launch_entry is None:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.CPU_REF_MISSING_LAUNCH_ENTRY",
                    "detail": "manifest.json extensions.cpu_ref.launch_entry is required for CPU reference packages.",
                    "manifest_field": "extensions.cpu_ref.launch_entry",
                }
            )
        if diagnostics:
            log_path = self._write_operation_log(
                kind="run",
                mode=self.mode,
                stage_id=stage_id,
                entry=entry,
                trace=trace,
                ok=False,
                diagnostics=diagnostics,
            )
            return RunResult(False, self.mode, entry, diagnostics=diagnostics, log_path=log_path)

        logical_entry = _entrypoint(self.manifest)
        if entry not in {logical_entry, str(launch_entry["function_name"])}:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.MISSING_ENTRYPOINT",
                    "detail": f"Entrypoint {entry!r} is not defined for the CPU reference package.",
                    "entry": entry,
                    "available_entries": [logical_entry, str(launch_entry["function_name"])],
                }
            )
            log_path = self._write_operation_log(
                kind="run",
                mode=self.mode,
                stage_id=stage_id,
                entry=entry,
                trace=trace,
                ok=False,
                diagnostics=diagnostics,
            )
            return RunResult(False, self.mode, entry, diagnostics=diagnostics, log_path=log_path)
        module = _load_python_module(
            self.package_dir / str(launch_entry["source"]), module_name=f"htp_cpu_ref_{stage_id}"
        )
        function_name = str(launch_entry["function_name"])
        result = getattr(module, function_name)(*args, mode=self.mode, trace=trace, runtime=None)
        metrics_path = _write_perf(
            self.package_dir,
            entry=logical_entry,
            backend="cpu_ref",
            runtime_ms=0.0,
            extra={"mode": self.mode},
        )
        trace_ref = _write_trace(
            self.package_dir,
            action="run",
            payload={"entry": logical_entry, "metrics": metrics_path},
        )
        log_path = self._write_operation_log(
            kind="run",
            mode=self.mode,
            stage_id=stage_id,
            entry=function_name,
            trace=trace,
            ok=True,
            diagnostics=[],
            trace_ref=trace_ref,
            adapter={"name": "cpu-ref"},
        )
        return RunResult(
            ok=True,
            mode=self.mode,
            entry=function_name,
            result={**result, "metrics": metrics_path, "trace_ref": trace_ref},
            trace_ref=trace_ref,
            diagnostics=[],
            log_path=log_path,
        )


class CPURefBinding(ManifestBinding):
    def validate(self) -> ValidationResult:
        base = super().validate()
        diagnostics = [
            diagnostic
            for diagnostic in base.diagnostics
            if diagnostic.get("code")
            not in {"HTP.BINDINGS.MISSING_BACKEND", "HTP.BINDINGS.MISSING_CONTRACT_FILE"}
        ]
        missing_files = list(base.missing_files)
        diagnostics.extend(
            {
                "code": "HTP.BINDINGS.CPU_REF_MISSING_CONTRACT_FILE",
                "detail": f"Missing required CPU reference artifact path: {missing_path}",
            }
            for missing_path in missing_files
        )
        diagnostics.extend(_validate_metadata(self.manifest))
        diagnostics.extend(_validate_codegen_contract(self.package_dir, self.manifest))
        return ValidationResult(
            ok=not diagnostics,
            backend=self.backend,
            variant=self.variant,
            diagnostics=diagnostics,
            missing_files=missing_files,
        )

    def build(self, *, mode: str = "sim", force: bool = False, cache_dir: Path | None = None) -> BuildResult:
        del force, cache_dir
        validation = self.validate()
        diagnostics = [*validation.diagnostics, *self._mode_diagnostics(mode)]
        built_outputs: list[str] = []
        trace_ref: str | None = None
        if not diagnostics:
            toolchain_manifest = json.loads(
                (self.package_dir / _CPU_REF_OUTPUTS["toolchain_manifest"]).read_text()
            )
            driver = toolchain_manifest["build_driver"]
            module = importlib.import_module(str(driver["module"]))
            built_outputs = list(getattr(module, str(driver["callable"]))(self.package_dir, self.manifest))
            trace_ref = _write_trace(
                self.package_dir,
                action="build",
                payload={"mode": mode, "built_outputs": built_outputs},
            )
        session = self.load(mode=mode)
        log_path = session._write_log(
            kind="build",
            stem=f"build_{self.backend}_{mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={mode}",
                f"validated={validation.ok and not self._mode_diagnostics(mode)}",
                f"built_outputs={tuple(built_outputs)!r}",
            ),
            refs={"trace_ref": trace_ref} if trace_ref is not None else None,
            diagnostics=diagnostics or None,
            adapter={"name": "cpu-ref"} if trace_ref is not None else None,
        )
        return BuildResult(
            ok=not diagnostics,
            mode=mode,
            built_outputs=built_outputs,
            log_paths=[log_path],
            trace_refs=[trace_ref] if trace_ref is not None else [],
            diagnostics=diagnostics,
        )

    def load(self, *, mode: str = "sim") -> LoadResult:
        validation = self.validate()
        diagnostics = [*validation.diagnostics, *self._mode_diagnostics(mode)]
        return CPURefLoadResult(
            package_dir=self.package_dir,
            manifest=self.manifest,
            backend=self.backend,
            variant=self.variant,
            mode=mode,
            diagnostics=diagnostics,
            ok=not diagnostics,
        )

    def correctness_suite(self, *, mode: str = "sim") -> dict[str, Any]:
        validation = self.validate()
        return {
            "name": "cpu_ref.package_suite",
            "mode": mode,
            "ok": validation.ok,
            "diagnostics": list(validation.diagnostics),
            "checks": [{"name": "cpu_ref_contract_validate", "ok": validation.ok}],
        }

    @staticmethod
    def _mode_diagnostics(mode: str) -> list[dict[str, Any]]:
        if mode in {"sim", "device"}:
            return []
        return [
            {
                "code": "HTP.BINDINGS.CPU_REF_UNSUPPORTED_MODE",
                "detail": f"CPU reference binding does not support mode {mode!r}.",
                "mode": mode,
            }
        ]


def _validate_metadata(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    target = manifest.get("target")
    if not isinstance(target, Mapping) or target.get("backend") != "cpu_ref":
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.CPU_REF_METADATA_MISMATCH",
                "detail": "Manifest target.backend must be 'cpu_ref' for CPU reference packages.",
                "manifest_field": "target.backend",
            }
        )
        return diagnostics
    outputs = manifest.get("outputs")
    if not isinstance(outputs, Mapping):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.CPU_REF_MISSING_METADATA",
                "detail": "manifest.json outputs is required for CPU reference packages.",
                "manifest_field": "outputs",
            }
        )
    else:
        for field, expected in _CPU_REF_OUTPUTS.items():
            value = outputs.get(field)
            if not isinstance(value, str):
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.CPU_REF_MISSING_METADATA",
                        "detail": f"manifest.json outputs.{field} is required for CPU reference packages.",
                        "manifest_field": f"outputs.{field}",
                    }
                )
            elif value != expected:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.CPU_REF_METADATA_MISMATCH",
                        "detail": f"manifest.json outputs.{field} must use the canonical CPU reference artifact path.",
                        "manifest_field": f"outputs.{field}",
                        "manifest_value": value,
                        "expected_value": expected,
                    }
                )
    extensions = manifest.get("extensions")
    cpu_ref_extension = extensions.get("cpu_ref") if isinstance(extensions, Mapping) else None
    if not isinstance(cpu_ref_extension, Mapping):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.CPU_REF_MISSING_METADATA",
                "detail": "manifest.json extensions.cpu_ref is required for CPU reference packages.",
                "manifest_field": "extensions.cpu_ref",
            }
        )
    return diagnostics


def _validate_codegen_contract(package_dir: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for required_path in _REQUIRED_PATHS:
        if not (package_dir / required_path).exists():
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.CPU_REF_MISSING_CONTRACT_FILE",
                    "detail": f"Missing required CPU reference artifact path: {required_path}",
                }
            )
    if diagnostics:
        return diagnostics
    codegen_index = json.loads((package_dir / _CPU_REF_OUTPUTS["cpu_ref_codegen_index"]).read_text())
    if codegen_index.get("schema") != CPU_REF_CODEGEN_SCHEMA_ID:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.CPU_REF_INVALID_SCHEMA",
                "detail": f"codegen/cpu_ref/cpu_ref_codegen.json must declare schema {CPU_REF_CODEGEN_SCHEMA_ID!r}.",
            }
        )
    toolchain = json.loads((package_dir / _CPU_REF_OUTPUTS["toolchain_manifest"]).read_text())
    if toolchain.get("schema") != CPU_REF_TOOLCHAIN_SCHEMA_ID:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.CPU_REF_INVALID_SCHEMA",
                "detail": f"build/toolchain.json must declare schema {CPU_REF_TOOLCHAIN_SCHEMA_ID!r}.",
            }
        )
    return diagnostics


def _entrypoint(manifest: Mapping[str, Any]) -> str:
    inputs = manifest.get("inputs")
    if isinstance(inputs, Mapping) and isinstance(inputs.get("entry"), str):
        return str(inputs["entry"])
    codegen_index = manifest.get("outputs", {})
    return str(codegen_index.get("entrypoint", ""))


def _launch_entry(manifest: Mapping[str, Any]) -> Mapping[str, Any] | None:
    extensions = manifest.get("extensions")
    if not isinstance(extensions, Mapping):
        return None
    cpu_ref = extensions.get("cpu_ref")
    if not isinstance(cpu_ref, Mapping):
        return None
    launch_entry = cpu_ref.get("launch_entry")
    return launch_entry if isinstance(launch_entry, Mapping) else None


def _load_python_module(module_path: Path, *, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Python module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_trace(package_dir: Path, *, action: str, payload: dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    relative_path = Path("logs") / f"adapter_cpu_ref_{action}_{timestamp}_{uuid4().hex[:8]}.json"
    trace_path = package_dir / relative_path
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "schema": ADAPTER_TRACE_SCHEMA_ID,
                "backend": "cpu_ref",
                "adapter": "python",
                "action": action,
                "payload": payload,
            },
            indent=2,
        )
        + "\n"
    )
    return relative_path.as_posix()


def _write_perf(
    package_dir: Path,
    *,
    entry: str,
    backend: str,
    runtime_ms: float,
    extra: Mapping[str, Any],
) -> str:
    relative_path = Path("metrics") / "perf.json"
    payload = {
        "schema": PERF_SCHEMA_ID,
        "entry": entry,
        "backend": backend,
        "runtime_ms": runtime_ms,
        **dict(extra),
    }
    perf_path = package_dir / relative_path
    perf_path.parent.mkdir(parents=True, exist_ok=True)
    perf_path.write_text(json.dumps(payload, indent=2) + "\n")
    return relative_path.as_posix()


__all__ = ["CPURefBinding", "build_reference_runtime"]
