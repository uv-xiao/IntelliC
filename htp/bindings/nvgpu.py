from __future__ import annotations

import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from htp.backends.nvgpu.arch import arch_for
from htp.backends.nvgpu.declarations import (
    NVGPU_PROJECT_DIR,
)
from htp.backends.nvgpu.declarations import (
    declaration_for as nvgpu_declaration_for,
)
from htp.backends.nvgpu.emit import (
    NVGPU_CODEGEN_SCHEMA_ID,
    NVGPU_TOOLCHAIN_SCHEMA_ID,
)
from htp.runtime.errors import ReplayDiagnosticError

from . import nvgpu_cuda_adapter
from .base import BuildResult, LoadResult, ManifestBinding, RunResult, ValidationResult


def _contract_outputs(variant: str | None) -> dict[str, str]:
    try:
        declaration = nvgpu_declaration_for(variant)
    except ValueError:
        declaration = nvgpu_declaration_for(None)
    return declaration.artifact_contract.as_manifest_outputs()


def _contract_profile(manifest: Mapping[str, Any], variant: str | None) -> str | None:
    target = manifest.get("target")
    if isinstance(target, Mapping):
        option = target.get("option")
        if isinstance(option, str):
            return option
        hardware_profile = target.get("hardware_profile")
        if isinstance(hardware_profile, str) and hardware_profile.startswith("nvidia:"):
            parts = hardware_profile.split(":")
            if len(parts) >= 2:
                return parts[1]
    return variant


class NVGPULoadResult(LoadResult):
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
        launch_entry = _resolve_launch_entry(self.manifest)
        if launch_entry is None:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_MISSING_LAUNCH_ENTRY",
                    "detail": "manifest.json extensions.nvgpu.launch_entry is required to run NV-GPU packages.",
                    "manifest_field": "extensions.nvgpu.launch_entry",
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
            return RunResult(
                ok=False,
                mode=self.mode,
                entry=entry,
                diagnostics=diagnostics,
                log_path=log_path,
            )

        expected_entry = _entrypoint_name(self.package_dir, self.manifest)
        function_name = launch_entry["function_name"]
        if entry not in {function_name, expected_entry}:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.MISSING_ENTRYPOINT",
                    "detail": f"Entrypoint {entry!r} is not defined for the NV-GPU package.",
                    "entry": entry,
                    "available_entries": [
                        name for name in (expected_entry, function_name) if name is not None
                    ],
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
            return RunResult(
                ok=False,
                mode=self.mode,
                entry=entry,
                diagnostics=diagnostics,
                log_path=log_path,
            )

        launch_path = self.package_dir / launch_entry["source"]
        if self.mode == "device":
            logical_entry = expected_entry if expected_entry is not None else function_name
            ok, result, adapter_diagnostics, trace_ref = nvgpu_cuda_adapter.run_package(
                self.package_dir,
                self.manifest,
                entry=logical_entry,
                args=args,
                kwargs={} if kwargs is None else kwargs,
            )
            diagnostics.extend(adapter_diagnostics)
            log_path = self._write_operation_log(
                kind="run",
                mode=self.mode,
                stage_id=stage_id,
                entry=function_name,
                trace=trace,
                ok=ok and not diagnostics,
                diagnostics=diagnostics,
                trace_ref=trace_ref,
                adapter={"name": "cuda-driver"} if trace_ref is not None else None,
            )
            return RunResult(
                ok=ok and not diagnostics,
                mode=self.mode,
                entry=function_name,
                result=result,
                trace_ref=trace_ref,
                diagnostics=diagnostics,
                log_path=log_path,
            )

        try:
            module = _load_python_module(launch_path, module_name=f"htp_nvgpu_launch_{stage_id}")
        except Exception as exc:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_RUN_LOAD_ERROR",
                    "detail": str(exc),
                    "entry": entry,
                    "launch_source": launch_entry["source"],
                    "exception_type": exc.__class__.__name__,
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
            return RunResult(
                ok=False,
                mode=self.mode,
                entry=entry,
                diagnostics=diagnostics,
                log_path=log_path,
            )

        try:
            result = getattr(module, function_name)(
                *args,
                mode=self.mode,
                trace=trace,
                **({} if kwargs is None else kwargs),
            )
        except ReplayDiagnosticError as exc:
            diagnostic = dict(exc.payload)
            diagnostic["code"] = exc.code
            if exc.fix_hints:
                diagnostic["fix_hints"] = list(exc.fix_hints)
            diagnostics.append(diagnostic)
            ok = False
            result = None
        except Exception as exc:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_RUN_EXECUTION_ERROR",
                    "detail": str(exc),
                    "entry": function_name,
                    "launch_source": launch_entry["source"],
                    "exception_type": exc.__class__.__name__,
                }
            )
            ok = False
            result = None
        else:
            ok = not diagnostics
        log_path = self._write_operation_log(
            kind="run",
            mode=self.mode,
            stage_id=stage_id,
            entry=function_name,
            trace=trace,
            ok=ok,
            diagnostics=diagnostics,
        )
        return RunResult(
            ok=ok,
            mode=self.mode,
            entry=function_name,
            result=result,
            diagnostics=diagnostics,
            log_path=log_path,
        )


class NVGPUBinding(ManifestBinding):
    def validate(self) -> ValidationResult:
        base_report = super().validate()
        missing_files = list(base_report.missing_files)
        diagnostics = [
            diagnostic
            for diagnostic in base_report.diagnostics
            if diagnostic.get("code")
            not in {"HTP.BINDINGS.MISSING_BACKEND", "HTP.BINDINGS.MISSING_CONTRACT_FILE"}
        ]
        if self._should_enforce_nvgpu_contract():
            diagnostics.extend(
                {
                    "code": "HTP.BINDINGS.NVGPU_MISSING_CONTRACT_FILE",
                    "detail": f"Missing required NV-GPU artifact path: {missing_path}",
                }
                for missing_path in missing_files
            )

        diagnostics.extend(self._validate_metadata())
        required_paths = self._required_paths()
        if self._should_enforce_nvgpu_contract():
            for required_path in required_paths:
                if required_path in missing_files:
                    continue
                if not (self.package_dir / required_path).exists():
                    missing_files.append(required_path)
                    diagnostics.append(
                        {
                            "code": "HTP.BINDINGS.NVGPU_MISSING_CONTRACT_FILE",
                            "detail": f"Missing required NV-GPU artifact path: {required_path}",
                        }
                    )
        if self._should_enforce_nvgpu_contract() and not missing_files:
            diagnostics.extend(
                self._validate_contract(
                    codegen_index_path=required_paths[0],
                    toolchain_manifest_path=required_paths[1],
                )
            )

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
        if validation.ok:
            codegen_index_path, toolchain_manifest_path = self._required_paths()
            built_outputs.extend(
                [
                    codegen_index_path,
                    toolchain_manifest_path,
                ]
            )
            launch_entry = _resolve_launch_entry(self.manifest)
            if launch_entry is not None:
                built_outputs.append(launch_entry["source"])
            built_outputs.extend(_kernel_sources(self.package_dir / codegen_index_path))
            if mode == "device":
                adapter_outputs, adapter_diagnostics, trace_ref = nvgpu_cuda_adapter.build_package(
                    self.package_dir,
                    self.manifest,
                    force=force,
                )
                built_outputs.extend(adapter_outputs)
                diagnostics.extend(adapter_diagnostics)
            else:
                trace_ref = None
                built_outputs.extend(_derived_outputs(self.package_dir / toolchain_manifest_path))
        else:
            trace_ref = None
        session = self.load(mode=mode)
        log_path = session._write_log(
            kind="build",
            stem=f"build_{self.backend}_{mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={mode}",
                f"validated={validation.ok}",
                f"built_outputs={tuple(built_outputs)!r}",
            ),
            refs={"trace_ref": trace_ref} if trace_ref is not None else None,
            diagnostics=diagnostics or None,
            adapter={"name": "nvcc"} if trace_ref is not None and mode == "device" else None,
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
        return NVGPULoadResult(
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
        diagnostics = [*validation.diagnostics, *self._mode_diagnostics(mode)]
        return {
            "name": "nvgpu.package_suite",
            "mode": mode,
            "ok": not diagnostics,
            "diagnostics": diagnostics,
            "checks": [
                {"name": "nvgpu_contract_validate", "ok": validation.ok},
                {"name": "nvgpu_mode_supported", "ok": not self._mode_diagnostics(mode)},
            ],
        }

    def _required_paths(self) -> tuple[str, str]:
        outputs_contract = _contract_outputs(_contract_profile(self.manifest, self.variant))
        outputs = self.manifest.get("outputs")
        if isinstance(outputs, Mapping):
            return (
                str(outputs.get("nvgpu_codegen_index", outputs_contract["nvgpu_codegen_index"])),
                str(outputs.get("toolchain_manifest", outputs_contract["toolchain_manifest"])),
            )
        return (outputs_contract["nvgpu_codegen_index"], outputs_contract["toolchain_manifest"])

    def _validate_metadata(self) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        outputs_contract = _contract_outputs(_contract_profile(self.manifest, self.variant))
        target = self.manifest.get("target")
        hardware_profile = target.get("hardware_profile") if isinstance(target, Mapping) else None
        if not isinstance(hardware_profile, str):
            diagnostics.append(self._missing_metadata_diagnostic("target.hardware_profile"))

        outputs = self.manifest.get("outputs")
        if not isinstance(outputs, Mapping):
            diagnostics.extend(
                [
                    self._missing_metadata_diagnostic("outputs.nvgpu_codegen_index"),
                    self._missing_metadata_diagnostic("outputs.toolchain_manifest"),
                ]
            )
        else:
            if not isinstance(outputs.get("nvgpu_codegen_index"), str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.nvgpu_codegen_index"))
            elif outputs.get("nvgpu_codegen_index") != outputs_contract["nvgpu_codegen_index"]:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                        "detail": "manifest.json outputs.nvgpu_codegen_index must use the canonical NV-GPU artifact path.",
                        "manifest_field": "outputs.nvgpu_codegen_index",
                        "manifest_value": outputs.get("nvgpu_codegen_index"),
                        "expected_value": outputs_contract["nvgpu_codegen_index"],
                    }
                )
            if not isinstance(outputs.get("toolchain_manifest"), str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.toolchain_manifest"))
            elif outputs.get("toolchain_manifest") != outputs_contract["toolchain_manifest"]:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                        "detail": "manifest.json outputs.toolchain_manifest must use the canonical NV-GPU artifact path.",
                        "manifest_field": "outputs.toolchain_manifest",
                        "manifest_value": outputs.get("toolchain_manifest"),
                        "expected_value": outputs_contract["toolchain_manifest"],
                    }
                )

        extension = self._nvgpu_extension()
        if extension is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.nvgpu"))
            return diagnostics
        for field in (
            "kernel_project_dir",
            "cuda_runtime_contract",
            "codegen_mode",
            "toolchain_manifest",
        ):
            if not isinstance(extension.get(field), str):
                diagnostics.append(self._missing_metadata_diagnostic(f"extensions.nvgpu.{field}"))
        launch_entry = extension.get("launch_entry")
        if not isinstance(launch_entry, Mapping):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.nvgpu.launch_entry"))
        else:
            if not isinstance(launch_entry.get("source"), str):
                diagnostics.append(self._missing_metadata_diagnostic("extensions.nvgpu.launch_entry.source"))
            if not isinstance(launch_entry.get("function_name"), str):
                diagnostics.append(
                    self._missing_metadata_diagnostic("extensions.nvgpu.launch_entry.function_name")
                )
        return diagnostics

    def _validate_contract(
        self,
        *,
        codegen_index_path: str,
        toolchain_manifest_path: str,
    ) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        target = self.manifest.get("target")
        manifest_backend = target.get("backend") if isinstance(target, Mapping) else None
        target_hardware_profile = target.get("hardware_profile") if isinstance(target, Mapping) else None
        try:
            codegen_index = json.loads((self.package_dir / codegen_index_path).read_text())
        except Exception as exc:
            return [
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                    "detail": str(exc),
                }
            ]
        if not isinstance(codegen_index, Mapping):
            return [
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                    "detail": "nvgpu_codegen.json must decode to a mapping.",
                }
            ]
        if codegen_index.get("schema") != NVGPU_CODEGEN_SCHEMA_ID:
            return [
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                    "detail": f"nvgpu_codegen.json must declare schema {NVGPU_CODEGEN_SCHEMA_ID!r}.",
                }
            ]

        try:
            toolchain_manifest = json.loads((self.package_dir / toolchain_manifest_path).read_text())
        except Exception as exc:
            return [
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": str(exc),
                }
            ]
        if not isinstance(toolchain_manifest, Mapping):
            return [
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": "build/toolchain.json must decode to a mapping.",
                }
            ]
        if toolchain_manifest.get("schema") != NVGPU_TOOLCHAIN_SCHEMA_ID:
            return [
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": f"build/toolchain.json must declare schema {NVGPU_TOOLCHAIN_SCHEMA_ID!r}.",
                }
            ]

        if manifest_backend != "nvgpu":
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                    "detail": "Manifest target.backend does not match NV-GPU binding selection.",
                    "field": "backend",
                    "manifest_field": "target.backend",
                    "manifest_value": manifest_backend,
                    "expected_value": "nvgpu",
                }
            )
        backend = codegen_index.get("backend")
        if backend != "nvgpu":
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                    "detail": "nvgpu_codegen.json backend does not match the NV-GPU binding contract.",
                    "field": "backend",
                    "codegen_field": f"{codegen_index_path}.backend",
                    "codegen_value": backend,
                    "expected_value": "nvgpu",
                }
            )
        if codegen_index.get("variant") != "cuda":
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                    "detail": "nvgpu_codegen.json variant must be 'cuda'.",
                }
            )
        if codegen_index.get("hardware_profile") != target_hardware_profile:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                    "detail": "Manifest target.hardware_profile does not match nvgpu_codegen.json.",
                    "field": "hardware_profile",
                    "manifest_field": "target.hardware_profile",
                    "manifest_value": target_hardware_profile,
                    "codegen_value": codegen_index.get("hardware_profile"),
                }
            )

        extension = self._nvgpu_extension()
        if extension is not None and extension.get("toolchain_manifest") != toolchain_manifest_path:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                    "detail": "manifest.json extensions.nvgpu.toolchain_manifest does not match outputs.toolchain_manifest.",
                    "manifest_field": "extensions.nvgpu.toolchain_manifest",
                    "manifest_value": extension.get("toolchain_manifest"),
                    "expected_value": toolchain_manifest_path,
                }
            )

        launch = codegen_index.get("launch")
        if not isinstance(launch, Mapping):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                    "detail": "nvgpu_codegen.json launch must be a mapping.",
                }
            )
        else:
            expected_source = str(launch.get("source", ""))
            if not (self.package_dir / expected_source).exists():
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.NVGPU_MISSING_CONTRACT_FILE",
                        "detail": f"Missing required NV-GPU artifact path: {expected_source}",
                    }
                )

        kernels = codegen_index.get("kernels")
        if not isinstance(kernels, list) or not kernels:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                    "detail": "nvgpu_codegen.json kernels must be a non-empty list.",
                }
            )
            return diagnostics
        for kernel in kernels:
            if not isinstance(kernel, Mapping):
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                        "detail": "nvgpu_codegen.json kernel entries must be mappings.",
                    }
                )
                continue
            kernel_source = kernel.get("source")
            if not isinstance(kernel_source, str):
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                        "detail": "nvgpu_codegen.json kernel source must be a string.",
                    }
                )
                continue
            if PurePosixPath(kernel_source).suffix != ".cu":
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX",
                        "detail": "nvgpu_codegen.json kernel source must point to a .cu file.",
                    }
                )
            if not (self.package_dir / kernel_source).exists():
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.NVGPU_MISSING_CONTRACT_FILE",
                        "detail": f"Missing required NV-GPU artifact path: {kernel_source}",
                    }
                )
        expected_arch = self._expected_arch()
        if toolchain_manifest.get("cuda_arches") != [*expected_arch.cuda_arches]:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                    "detail": "build/toolchain.json cuda_arches does not match the hardware profile contract.",
                    "toolchain_field": "build/toolchain.json.cuda_arches",
                    "toolchain_value": toolchain_manifest.get("cuda_arches"),
                    "expected_value": [*expected_arch.cuda_arches],
                }
            )
        if extension is not None and isinstance(launch, Mapping):
            project_dir = str(extension.get("kernel_project_dir"))
            launch_entry = extension.get("launch_entry")
            if isinstance(launch_entry, Mapping):
                launch_source = launch.get("source")
                if isinstance(launch_source, str):
                    launch_source_path = PurePosixPath(launch_source)
                    project_dir_path = PurePosixPath(project_dir)
                    try:
                        normalized_launch_source = launch_source_path.relative_to(project_dir_path).as_posix()
                    except ValueError:
                        normalized_launch_source = None
                    if launch_entry.get("source") != normalized_launch_source:
                        diagnostics.append(
                            {
                                "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                                "detail": "manifest.json extensions.nvgpu.launch_entry.source does not match nvgpu_codegen.json launch.source after project-relative normalization.",
                                "manifest_field": "extensions.nvgpu.launch_entry.source",
                                "manifest_value": launch_entry.get("source"),
                                "codegen_field": f"{codegen_index_path}.launch.source",
                                "codegen_value": launch_source,
                            }
                        )
                if launch_entry.get("function_name") != launch.get("function_name"):
                    diagnostics.append(
                        {
                            "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                            "detail": "manifest.json extensions.nvgpu.launch_entry.function_name does not match nvgpu_codegen.json launch.function_name.",
                            "manifest_field": "extensions.nvgpu.launch_entry.function_name",
                            "manifest_value": launch_entry.get("function_name"),
                            "codegen_field": f"{codegen_index_path}.launch.function_name",
                            "codegen_value": launch.get("function_name"),
                        }
                    )
        return diagnostics

    def _expected_arch(self):
        hardware_profile = (
            self.manifest.get("target", {}).get("hardware_profile")
            if isinstance(self.manifest.get("target"), Mapping)
            else None
        )
        if hardware_profile == "nvidia:blackwell:sm100":
            return arch_for("blackwell")
        return arch_for("ampere")

    def _nvgpu_extension(self) -> Mapping[str, Any] | None:
        extensions = self.manifest.get("extensions")
        if not isinstance(extensions, Mapping):
            return None
        extension = extensions.get("nvgpu")
        if not isinstance(extension, Mapping):
            return None
        return extension

    def _should_enforce_nvgpu_contract(self) -> bool:
        target = self.manifest.get("target")
        backend = target.get("backend") if isinstance(target, Mapping) else None
        if backend == "nvgpu":
            return True
        return self._nvgpu_extension() is not None or (self.package_dir / NVGPU_PROJECT_DIR).exists()

    def _mode_diagnostics(self, mode: str) -> list[dict[str, Any]]:
        if mode in {"sim", "device"}:
            return []
        return [
            {
                "code": "HTP.BINDINGS.INVALID_MODE",
                "detail": f"Unsupported NV-GPU binding mode: {mode!r}.",
                "mode": mode,
                "supported_modes": ["sim", "device"],
            }
        ]

    @staticmethod
    def _missing_metadata_diagnostic(field: str) -> dict[str, Any]:
        return {
            "code": "HTP.BINDINGS.NVGPU_MISSING_METADATA",
            "detail": f"manifest.json {field} is required for NV-GPU packages.",
            "manifest_field": field,
        }


__all__ = ["NVGPUBinding"]


def _resolve_launch_entry(manifest: Mapping[str, Any]) -> dict[str, str] | None:
    extensions = manifest.get("extensions")
    if not isinstance(extensions, Mapping):
        return None
    nvgpu = extensions.get("nvgpu")
    if not isinstance(nvgpu, Mapping):
        return None
    launch_entry = nvgpu.get("launch_entry")
    if not isinstance(launch_entry, Mapping):
        return None
    source = launch_entry.get("source")
    function_name = launch_entry.get("function_name")
    if not isinstance(source, str) or not isinstance(function_name, str):
        return None
    return {"source": str(NVGPU_PROJECT_DIR / source), "function_name": function_name}


def _entrypoint_name(package_dir: Path, manifest: Mapping[str, Any]) -> str | None:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, Mapping):
        return None
    codegen_index_path = outputs.get("nvgpu_codegen_index")
    if not isinstance(codegen_index_path, str):
        return None
    try:
        codegen_index = json.loads((package_dir / codegen_index_path).read_text())
    except Exception:
        return None
    entrypoint = codegen_index.get("entrypoint")
    if not isinstance(entrypoint, str):
        return None
    return entrypoint


def _kernel_sources(codegen_index_path: Path) -> list[str]:
    try:
        codegen_index = json.loads(codegen_index_path.read_text())
    except Exception:
        return []
    kernels = codegen_index.get("kernels")
    if not isinstance(kernels, list):
        return []
    return [
        str(kernel["source"])
        for kernel in kernels
        if isinstance(kernel, Mapping) and isinstance(kernel.get("source"), str)
    ]


def _derived_outputs(toolchain_manifest_path: Path) -> list[str]:
    try:
        toolchain_manifest = json.loads(toolchain_manifest_path.read_text())
    except Exception:
        return []
    derived_outputs = toolchain_manifest.get("derived_outputs")
    if not isinstance(derived_outputs, list):
        return []
    return [str(path) for path in derived_outputs if isinstance(path, str)]


def _load_python_module(module_path: Path, *, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Python module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
