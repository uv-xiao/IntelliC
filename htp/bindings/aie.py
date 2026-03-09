from __future__ import annotations

import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from htp_ext.aie.declarations import declaration_for
from htp_ext.aie.emit import AIE_CODEGEN_SCHEMA_ID, AIE_TOOLCHAIN_SCHEMA_ID
from htp_ext.aie.toolchain import AIE_BUILD_PRODUCT_SCHEMA_ID, AIE_HOST_RUNTIME_SCHEMA_ID

from . import aie_toolchain_adapter
from .base import BuildResult, LoadResult, ManifestBinding, RunResult, ValidationResult

_AIE_OUTPUTS = declaration_for().artifact_contract.as_manifest_outputs()
_REQUIRED_PATHS = (
    "codegen/aie/aie.mlir",
    "codegen/aie/mapping.json",
    "codegen/aie/fifos.json",
    "codegen/aie/host.py",
    _AIE_OUTPUTS["aie_codegen_index"],
    _AIE_OUTPUTS["toolchain_manifest"],
)


class AIELoadResult(LoadResult):
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
            return RunResult(
                ok=False,
                mode=self.mode,
                entry=entry,
                diagnostics=diagnostics,
                log_path=log_path,
            )

        ok, result, adapter_diagnostics, trace_ref = aie_toolchain_adapter.run_package(
            self.package_dir,
            self.manifest,
            mode=self.mode,
            entry=entry,
            args=args,
            kwargs={} if kwargs is None else kwargs,
        )
        diagnostics.extend(adapter_diagnostics)
        log_path = self._write_operation_log(
            kind="run",
            mode=self.mode,
            stage_id=stage_id,
            entry=entry,
            trace=trace,
            ok=ok and not diagnostics,
            diagnostics=diagnostics,
            trace_ref=trace_ref,
            adapter={"name": "aie-host"} if trace_ref is not None else None,
        )
        return RunResult(
            ok=ok and not diagnostics,
            mode=self.mode,
            entry=entry,
            result=result,
            trace_ref=trace_ref,
            diagnostics=diagnostics,
            log_path=log_path,
        )


class AIEBinding(ManifestBinding):
    def validate(self) -> ValidationResult:
        base_report = super().validate()
        missing_files = list(base_report.missing_files)
        diagnostics = [
            diagnostic
            for diagnostic in base_report.diagnostics
            if diagnostic.get("code")
            not in {"HTP.BINDINGS.MISSING_BACKEND", "HTP.BINDINGS.MISSING_CONTRACT_FILE"}
        ]
        diagnostics.extend(
            {
                "code": "HTP.BINDINGS.AIE_MISSING_CONTRACT_FILE",
                "detail": f"Missing required AIE artifact path: {missing_path}",
            }
            for missing_path in missing_files
        )
        for required_path in _REQUIRED_PATHS:
            if required_path in missing_files:
                continue
            if not (self.package_dir / required_path).exists():
                missing_files.append(required_path)
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.AIE_MISSING_CONTRACT_FILE",
                        "detail": f"Missing required AIE artifact path: {required_path}",
                    }
                )
        diagnostics.extend(_validate_metadata(self.manifest))
        if not missing_files:
            diagnostics.extend(_validate_codegen_contract(self.package_dir, self.manifest))
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
        del cache_dir
        validation = self.validate()
        diagnostics = [*validation.diagnostics, *self._mode_diagnostics(mode)]
        built_outputs: list[str] = []
        if not diagnostics:
            built_outputs, adapter_diagnostics, trace_ref = aie_toolchain_adapter.build_package(
                self.package_dir,
                self.manifest,
                mode=mode,
                force=force,
            )
            diagnostics.extend(adapter_diagnostics)
        else:
            trace_ref = None
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
            adapter={"name": "aie-toolchain"} if trace_ref is not None else None,
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
        return AIELoadResult(
            package_dir=self.package_dir,
            manifest=self.manifest,
            backend=self.backend,
            variant=self.variant,
            mode=mode,
            diagnostics=diagnostics,
            ok=not diagnostics,
        )

    def correctness_suite(self, *, mode: str = "sim") -> dict[str, Any]:
        del mode
        validation = self.validate()
        return {
            "name": "aie.package_suite",
            "mode": "artifact",
            "ok": validation.ok,
            "diagnostics": list(validation.diagnostics),
            "checks": [{"name": "aie_contract_validate", "ok": validation.ok}],
        }

    @staticmethod
    def _mode_diagnostics(mode: str) -> list[dict[str, Any]]:
        if mode in {"sim", "device"}:
            return []
        return [
            {
                "code": "HTP.BINDINGS.AIE_UNSUPPORTED_MODE",
                "detail": f"AIE binding does not support mode {mode!r}.",
                "mode": mode,
            }
        ]


def _validate_metadata(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    target = manifest.get("target")
    if not isinstance(target, Mapping) or target.get("backend") != "aie":
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_METADATA_MISMATCH",
                "detail": "Manifest target.backend must be 'aie' for AIE packages.",
                "manifest_field": "target.backend",
            }
        )
        return diagnostics
    extensions = manifest.get("extensions")
    if not isinstance(extensions, Mapping) or not isinstance(extensions.get("aie"), Mapping):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_MISSING_METADATA",
                "detail": "manifest.json extensions.aie is required for AIE packages.",
                "manifest_field": "extensions.aie",
            }
        )
        return diagnostics
    outputs = manifest.get("outputs")
    if not isinstance(outputs, Mapping):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_MISSING_METADATA",
                "detail": "manifest.json outputs is required for AIE packages.",
                "manifest_field": "outputs",
            }
        )
    else:
        for field, expected in _AIE_OUTPUTS.items():
            value = outputs.get(field)
            if not isinstance(value, str):
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.AIE_MISSING_METADATA",
                        "detail": f"manifest.json outputs.{field} is required for AIE packages.",
                        "manifest_field": f"outputs.{field}",
                    }
                )
            elif value != expected:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.AIE_METADATA_MISMATCH",
                        "detail": f"manifest.json outputs.{field} must use the canonical AIE artifact path.",
                        "manifest_field": f"outputs.{field}",
                        "manifest_value": value,
                        "expected_value": expected,
                    }
                )
    aie_extension = extensions["aie"]
    if aie_extension.get("mlir") != "codegen/aie/aie.mlir":
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_METADATA_MISMATCH",
                "detail": "extensions.aie.mlir must point to codegen/aie/aie.mlir.",
                "manifest_field": "extensions.aie.mlir",
                "manifest_value": aie_extension.get("mlir"),
                "expected_value": "codegen/aie/aie.mlir",
            }
        )
    if aie_extension.get("toolchain_manifest") != _AIE_OUTPUTS["toolchain_manifest"]:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_METADATA_MISMATCH",
                "detail": "extensions.aie.toolchain_manifest must point to the canonical AIE toolchain manifest.",
                "manifest_field": "extensions.aie.toolchain_manifest",
                "manifest_value": aie_extension.get("toolchain_manifest"),
                "expected_value": _AIE_OUTPUTS["toolchain_manifest"],
            }
        )
    return diagnostics


def _validate_codegen_contract(package_dir: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    try:
        codegen_index = json.loads((package_dir / _AIE_OUTPUTS["aie_codegen_index"]).read_text())
    except Exception as exc:
        return [
            {
                "code": "HTP.BINDINGS.AIE_INVALID_CODEGEN_INDEX",
                "detail": str(exc),
            }
        ]
    if not isinstance(codegen_index, Mapping) or codegen_index.get("schema") != AIE_CODEGEN_SCHEMA_ID:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_INVALID_CODEGEN_INDEX",
                "detail": f"codegen/aie/aie_codegen.json must declare schema {AIE_CODEGEN_SCHEMA_ID!r}.",
            }
        )
        return diagnostics

    try:
        toolchain_manifest = json.loads((package_dir / _AIE_OUTPUTS["toolchain_manifest"]).read_text())
    except Exception as exc:
        return [
            {
                "code": "HTP.BINDINGS.AIE_INVALID_TOOLCHAIN_MANIFEST",
                "detail": str(exc),
            }
        ]
    if (
        not isinstance(toolchain_manifest, Mapping)
        or toolchain_manifest.get("schema") != AIE_TOOLCHAIN_SCHEMA_ID
    ):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_INVALID_TOOLCHAIN_MANIFEST",
                "detail": f"codegen/aie/toolchain.json must declare schema {AIE_TOOLCHAIN_SCHEMA_ID!r}.",
            }
        )
        return diagnostics

    driver = toolchain_manifest.get("build_driver")
    if not isinstance(driver, Mapping) or driver.get("module") != "htp_ext.aie.toolchain":
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_INVALID_TOOLCHAIN_MANIFEST",
                "detail": "AIE toolchain manifest must declare the reference build driver.",
            }
        )
    if toolchain_manifest.get("build_product_schema") != AIE_BUILD_PRODUCT_SCHEMA_ID:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_INVALID_TOOLCHAIN_MANIFEST",
                "detail": f"AIE toolchain manifest must declare build_product_schema {AIE_BUILD_PRODUCT_SCHEMA_ID!r}.",
            }
        )
    if toolchain_manifest.get("host_runtime_schema") != AIE_HOST_RUNTIME_SCHEMA_ID:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_INVALID_TOOLCHAIN_MANIFEST",
                "detail": f"AIE toolchain manifest must declare host_runtime_schema {AIE_HOST_RUNTIME_SCHEMA_ID!r}.",
            }
        )

    host_path = package_dir / "codegen" / "aie" / "host.py"
    try:
        module = _load_python_module(host_path, module_name="htp_aie_host_runtime")
    except Exception as exc:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_INVALID_HOST_RUNTIME",
                "detail": str(exc),
            }
        )
        return diagnostics
    if not hasattr(module, "launch"):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.AIE_INVALID_HOST_RUNTIME",
                "detail": "codegen/aie/host.py must define launch(...).",
            }
        )
    return diagnostics


def _load_python_module(module_path: Path, *, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Python module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


__all__ = ["AIEBinding"]
