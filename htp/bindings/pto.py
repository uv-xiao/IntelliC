from __future__ import annotations

import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from htp.backends.pto.arch import arch_for
from htp.backends.pto.emit import (
    PTO_CODEGEN_SCHEMA_ID,
    PTO_PROJECT_DIR,
    PTO_TOOLCHAIN_PATH,
    PTO_TOOLCHAIN_SCHEMA_ID,
)

from . import pto_runtime_adapter
from .base import BuildResult, LoadResult, ManifestBinding, RunResult, ValidationResult

DEFAULT_KERNEL_CONFIG = (PTO_PROJECT_DIR / "kernel_config.py").as_posix()
DEFAULT_CODEGEN_INDEX = (PTO_PROJECT_DIR / "pto_codegen.json").as_posix()
DEFAULT_TOOLCHAIN_MANIFEST = PTO_TOOLCHAIN_PATH.as_posix()


class PTOLoadResult(LoadResult):
    def run(
        self,
        entry: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        trace: str = "off",
    ) -> RunResult:
        if not _has_pto_contract(self.package_dir, self.manifest):
            return super().run(entry, args=args, kwargs=kwargs, trace=trace)

        stage_id = self._resolve_current_stage_id()
        ok, result, adapter_diagnostics = pto_runtime_adapter.run_package(
            self.package_dir,
            self.manifest,
            mode=self.mode,
            entry=entry,
            args=args,
            kwargs={} if kwargs is None else kwargs,
        )
        diagnostics = list(self.diagnostics)
        diagnostics.extend(adapter_diagnostics)
        log_path = self._write_operation_log(
            kind="run",
            mode=self.mode,
            stage_id=stage_id,
            entry=entry,
            trace=trace,
            ok=ok and not diagnostics,
            diagnostics=diagnostics,
        )
        return RunResult(
            ok=ok and not diagnostics,
            mode=self.mode,
            entry=entry,
            result=result,
            diagnostics=diagnostics,
            log_path=log_path,
        )


class PTOBinding(ManifestBinding):
    def validate(self) -> ValidationResult:
        base_report = super().validate()
        missing_files = list(base_report.missing_files)
        diagnostics = [
            diagnostic
            for diagnostic in base_report.diagnostics
            if diagnostic.get("code") != "HTP.BINDINGS.MISSING_BACKEND"
        ]
        required_paths = self._required_paths()
        diagnostics.extend(self._validate_required_metadata(required_paths=required_paths))

        if self._should_enforce_pto_contract():
            for required_path in required_paths:
                if required_path in missing_files:
                    continue
                if not (self.package_dir / required_path).exists():
                    missing_files.append(required_path)
                    diagnostics.append(
                        {
                            "code": "HTP.BINDINGS.PTO_MISSING_CONTRACT_FILE",
                            "detail": f"Missing required PTO artifact path: {required_path}",
                        }
                    )

        has_blocking_metadata = any(
            diagnostic.get("code")
            in {"HTP.BINDINGS.PTO_MISSING_METADATA", "HTP.BINDINGS.PTO_INVALID_TARGET_VARIANT"}
            for diagnostic in diagnostics
        )
        if self._should_enforce_pto_contract() and not missing_files and not has_blocking_metadata:
            diagnostics.extend(
                self._validate_pto_contract(
                    kernel_config_path=required_paths[0],
                    codegen_index_path=required_paths[1],
                    toolchain_manifest_path=required_paths[2],
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
        mode_diagnostics = self._mode_diagnostics(mode)
        diagnostics = [*validation.diagnostics, *mode_diagnostics]
        built_outputs: list[str] = []
        if not diagnostics:
            built_outputs, adapter_diagnostics = pto_runtime_adapter.build_package(
                self.package_dir,
                self.manifest,
                mode=mode,
                force=force,
            )
            diagnostics.extend(adapter_diagnostics)
        session = self.load(mode=mode)
        log_path = session._write_log(
            kind="build",
            stem=f"build_{self.backend}_{mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={mode}",
                f"platform={self._platform_for_mode(mode)}",
                f"validated={validation.ok and not mode_diagnostics}",
                f"built_outputs={tuple(built_outputs)!r}",
            ),
        )
        return BuildResult(
            ok=not diagnostics,
            mode=mode,
            built_outputs=built_outputs,
            log_paths=[log_path],
            diagnostics=diagnostics,
        )

    def load(self, *, mode: str = "sim") -> LoadResult:
        validation = self.validate()
        diagnostics = [*validation.diagnostics, *self._mode_diagnostics(mode)]
        return PTOLoadResult(
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
        checks = [
            {"name": "pto_contract_validate", "ok": validation.ok},
            {
                "name": "pto_runtime_platform",
                "ok": not self._mode_diagnostics(mode),
            },
        ]
        diagnostics = [*validation.diagnostics, *self._mode_diagnostics(mode)]
        return {
            "name": "pto.package_suite",
            "mode": mode,
            "ok": not diagnostics,
            "diagnostics": diagnostics,
            "checks": checks,
        }

    def _validate_pto_contract(
        self,
        *,
        kernel_config_path: str,
        codegen_index_path: str,
        toolchain_manifest_path: str,
    ) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []

        try:
            kernel_config = _load_python_module(
                self.package_dir / kernel_config_path, module_name="htp_pto_kernel_config"
            )
        except Exception as exc:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": str(exc),
                }
            )
            return diagnostics

        try:
            codegen_index = json.loads((self.package_dir / codegen_index_path).read_text())
        except Exception as exc:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_CODEGEN_INDEX",
                    "detail": str(exc),
                }
            )
            return diagnostics
        if not isinstance(codegen_index, Mapping):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_CODEGEN_INDEX",
                    "detail": "pto_codegen.json must decode to a mapping.",
                }
            )
            return diagnostics
        if codegen_index.get("schema") != PTO_CODEGEN_SCHEMA_ID:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_CODEGEN_INDEX",
                    "detail": f"pto_codegen.json must declare schema {PTO_CODEGEN_SCHEMA_ID!r}.",
                }
            )
            return diagnostics

        try:
            toolchain_manifest = json.loads((self.package_dir / toolchain_manifest_path).read_text())
        except Exception as exc:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": str(exc),
                }
            )
            return diagnostics
        if not isinstance(toolchain_manifest, Mapping):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": "build/toolchain.json must decode to a mapping.",
                }
            )
            return diagnostics
        if toolchain_manifest.get("schema") != PTO_TOOLCHAIN_SCHEMA_ID:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": f"build/toolchain.json must declare schema {PTO_TOOLCHAIN_SCHEMA_ID!r}.",
                }
            )
            return diagnostics

        kernels = getattr(kernel_config, "KERNELS", None)
        orchestration = getattr(kernel_config, "ORCHESTRATION", None)
        runtime_config = getattr(kernel_config, "RUNTIME_CONFIG", None)

        if not isinstance(kernels, list):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": "kernel_config.py must define KERNELS as a list.",
                }
            )
        elif not all(isinstance(kernel, Mapping) for kernel in kernels):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": "kernel_config.py KERNELS entries must be mappings.",
                }
            )
        elif not all(isinstance(kernel.get("func_id"), int) for kernel in kernels):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": "kernel_config.py KERNELS func_id values must be integers.",
                }
            )
        if not isinstance(orchestration, Mapping):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": "kernel_config.py must define ORCHESTRATION as a mapping.",
                }
            )
        if not isinstance(runtime_config, Mapping):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": "kernel_config.py must define RUNTIME_CONFIG as a mapping.",
                }
            )
        elif not isinstance(runtime_config.get("runtime"), str):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": "kernel_config.py RUNTIME_CONFIG.runtime must be a string.",
                }
            )
        if diagnostics:
            return diagnostics

        index_kernels = codegen_index.get("kernels")
        if not isinstance(index_kernels, list):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_CODEGEN_INDEX",
                    "detail": "pto_codegen.json must define kernels as a list.",
                }
            )
            return diagnostics
        if not all(isinstance(kernel, Mapping) for kernel in index_kernels):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_CODEGEN_INDEX",
                    "detail": "pto_codegen.json kernels entries must be mappings.",
                }
            )
            return diagnostics

        normalized_index_kernels = [
            {
                "func_id": kernel.get("func_id"),
                "source": self._project_relative(str(kernel.get("source", ""))),
                "core_type": kernel.get("core_type"),
            }
            for kernel in index_kernels
        ]
        if kernels != normalized_index_kernels:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "kernel_config.py KERNELS does not match pto_codegen.json.",
                }
            )

        index_orchestration = codegen_index.get("orchestration")
        normalized_index_orchestration = {
            "source": self._project_relative(str(index_orchestration.get("source", "")))
            if isinstance(index_orchestration, Mapping)
            else None,
            "function_name": index_orchestration.get("function_name")
            if isinstance(index_orchestration, Mapping)
            else None,
        }
        if dict(orchestration) != normalized_index_orchestration:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "kernel_config.py ORCHESTRATION does not match pto_codegen.json.",
                }
            )

        manifest_pto_extension = self._pto_extension()
        if manifest_pto_extension is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto"))
            return diagnostics

        codegen_backend = (
            codegen_index.get("backend") if isinstance(codegen_index.get("backend"), str) else None
        )
        if self.backend != codegen_backend:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                    "detail": "PTO metadata backend does not agree across manifest target and pto_codegen.json.",
                    "field": "backend",
                    "manifest_field": "target.backend",
                    "codegen_field": f"{codegen_index_path}.backend",
                    "manifest_value": self.backend,
                    "codegen_value": codegen_backend,
                }
            )

        extension_platform = (
            manifest_pto_extension.get("platform")
            if isinstance(manifest_pto_extension.get("platform"), str)
            else None
        )
        codegen_variant = (
            codegen_index.get("variant") if isinstance(codegen_index.get("variant"), str) else None
        )
        kernel_platform = (
            runtime_config.get("platform") if isinstance(runtime_config.get("platform"), str) else None
        )
        if (
            self.variant != extension_platform
            or self.variant != codegen_variant
            or self.variant != kernel_platform
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                    "detail": "PTO metadata variant/platform does not agree across manifest target, manifest extensions, kernel_config.py, and pto_codegen.json.",
                    "field": "variant",
                    "manifest_field": "target.variant",
                    "extension_field": "extensions.pto.platform",
                    "kernel_config_field": "kernel_config.py:RUNTIME_CONFIG.platform",
                    "codegen_field": f"{codegen_index_path}.variant",
                    "manifest_value": self.variant,
                    "extension_value": extension_platform,
                    "kernel_config_value": kernel_platform,
                    "codegen_value": codegen_variant,
                }
            )

        manifest_kernel_project_dir = manifest_pto_extension.get("kernel_project_dir")
        if not isinstance(manifest_kernel_project_dir, str):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.kernel_project_dir"))
        elif manifest_kernel_project_dir != PTO_PROJECT_DIR.as_posix():
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "manifest.json extensions.pto.kernel_project_dir does not match the emitted PTO project directory.",
                    "manifest_field": "extensions.pto.kernel_project_dir",
                }
            )

        manifest_toolchain_manifest = manifest_pto_extension.get("toolchain_manifest")
        if not isinstance(manifest_toolchain_manifest, str):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.toolchain_manifest"))
        elif manifest_toolchain_manifest != toolchain_manifest_path:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "manifest.json extensions.pto.toolchain_manifest does not match the PTO toolchain manifest path.",
                    "manifest_field": "extensions.pto.toolchain_manifest",
                }
            )

        manifest_runtime_config = manifest_pto_extension.get("runtime_config")
        if manifest_runtime_config is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.runtime_config"))
        else:
            expected_manifest_runtime_config = {
                key: value for key, value in dict(runtime_config).items() if key != "platform"
            }
            if (
                not isinstance(manifest_runtime_config, Mapping)
                or dict(manifest_runtime_config) != expected_manifest_runtime_config
            ):
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                        "detail": "manifest.json extensions.pto.runtime_config does not match kernel_config.py RUNTIME_CONFIG.",
                        "manifest_field": "extensions.pto.runtime_config",
                    }
                )

        manifest_orchestration_entry = manifest_pto_extension.get("orchestration_entry")
        if manifest_orchestration_entry is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.orchestration_entry"))
        elif not isinstance(manifest_orchestration_entry, Mapping) or dict(
            manifest_orchestration_entry
        ) != dict(orchestration):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "manifest.json extensions.pto.orchestration_entry does not match kernel_config.py ORCHESTRATION.",
                    "manifest_field": "extensions.pto.orchestration_entry",
                }
            )

        diagnostics.extend(
            self._validate_toolchain_manifest(
                toolchain_manifest=toolchain_manifest,
                manifest_pto_extension=manifest_pto_extension,
                toolchain_manifest_path=toolchain_manifest_path,
            )
        )

        for kernel in kernels:
            source = kernel.get("source")
            if isinstance(source, str) and not (self._project_dir() / source).exists():
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                        "detail": f"kernel_config.py references missing PTO source: {source}",
                    }
                )
        orchestration_source = orchestration.get("source")
        if (
            isinstance(orchestration_source, str)
            and not (self._project_dir() / orchestration_source).exists()
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": f"kernel_config.py references missing PTO source: {orchestration_source}",
                }
            )

        return diagnostics

    def _required_paths(self) -> tuple[str, str, str]:
        outputs = self.manifest.get("outputs")
        if not isinstance(outputs, Mapping):
            return DEFAULT_KERNEL_CONFIG, DEFAULT_CODEGEN_INDEX, DEFAULT_TOOLCHAIN_MANIFEST

        kernel_config = outputs.get("kernel_config")
        codegen_index = outputs.get("pto_codegen_index")
        toolchain_manifest = outputs.get("toolchain_manifest")
        return (
            kernel_config if isinstance(kernel_config, str) else DEFAULT_KERNEL_CONFIG,
            codegen_index if isinstance(codegen_index, str) else DEFAULT_CODEGEN_INDEX,
            toolchain_manifest if isinstance(toolchain_manifest, str) else DEFAULT_TOOLCHAIN_MANIFEST,
        )

    def _should_enforce_pto_contract(self) -> bool:
        if self.backend == "pto":
            return True

        outputs = self.manifest.get("outputs")
        if isinstance(outputs, Mapping) and (
            isinstance(outputs.get("kernel_config"), str)
            or isinstance(outputs.get("pto_codegen_index"), str)
            or isinstance(outputs.get("toolchain_manifest"), str)
        ):
            return True

        extensions = self.manifest.get("extensions")
        if isinstance(extensions, Mapping) and isinstance(extensions.get("pto"), Mapping):
            return True

        return (self.package_dir / PTO_PROJECT_DIR).exists()

    def _pto_extension(self) -> Mapping[str, Any] | None:
        extensions = self.manifest.get("extensions")
        if not isinstance(extensions, Mapping):
            return None
        pto_extension = extensions.get("pto")
        if not isinstance(pto_extension, Mapping):
            return None
        return pto_extension

    def _project_dir(self) -> Path:
        pto_extension = self._pto_extension()
        if pto_extension is not None:
            project_dir = pto_extension.get("kernel_project_dir")
            if isinstance(project_dir, str):
                return self.package_dir / project_dir
        return self.package_dir / PTO_PROJECT_DIR

    def _project_relative(self, path: str) -> str:
        try:
            return Path(path).relative_to(PTO_PROJECT_DIR).as_posix()
        except ValueError:
            return path

    def _platform_for_mode(self, mode: str) -> str:
        if mode == "device":
            return "a2a3"
        return "a2a3sim"

    def _mode_diagnostics(self, mode: str) -> list[dict[str, Any]]:
        if mode not in {"sim", "device"}:
            return [
                {
                    "code": "HTP.BINDINGS.INVALID_MODE",
                    "detail": f"Unsupported PTO binding mode: {mode!r}.",
                    "mode": mode,
                    "supported_modes": ["sim", "device"],
                }
            ]
        expected_platform = self._platform_for_mode(mode)
        if self.variant == expected_platform:
            return []
        return [
            {
                "code": "HTP.BINDINGS.PTO_MODE_PLATFORM_MISMATCH",
                "detail": f"PTO package variant {self.variant!r} is not runnable in mode {mode!r}.",
                "mode": mode,
                "manifest_field": "target.variant",
                "manifest_value": self.variant,
                "expected_platform": expected_platform,
            }
        ]

    def _validate_required_metadata(self, *, required_paths: tuple[str, str, str]) -> list[dict[str, Any]]:
        if not self._should_enforce_pto_contract():
            return []

        diagnostics: list[dict[str, Any]] = []
        target = self._target_record()
        target_backend = target.get("backend") if isinstance(target.get("backend"), str) else None
        if target_backend != self.backend:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                    "detail": "Manifest target.backend does not match PTO binding selection.",
                    "field": "backend",
                    "manifest_field": "target.backend",
                    "manifest_value": target_backend,
                    "expected_value": self.backend,
                }
            )
        variant_is_valid = self._has_valid_variant()
        if self.variant is None:
            diagnostics.append(self._missing_metadata_diagnostic("target.variant"))
        elif not variant_is_valid:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_TARGET_VARIANT",
                    "detail": f"Unsupported PTO variant {self.variant!r}; expected one of: a2a3sim, a2a3",
                    "manifest_field": "target.variant",
                    "manifest_value": self.variant,
                }
            )

        target_hardware_profile = (
            target.get("hardware_profile") if isinstance(target.get("hardware_profile"), str) else None
        )
        if target_hardware_profile is None:
            diagnostics.append(self._missing_metadata_diagnostic("target.hardware_profile"))
        elif self.variant is not None and variant_is_valid:
            try:
                expected_profile = arch_for(self.variant).hardware_profile
            except ValueError as exc:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_INVALID_TARGET_VARIANT",
                        "detail": str(exc),
                        "manifest_field": "target.variant",
                        "manifest_value": self.variant,
                    }
                )
            else:
                if target_hardware_profile != expected_profile:
                    diagnostics.append(
                        {
                            "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                            "detail": "PTO metadata hardware_profile does not agree with target.variant.",
                            "field": "hardware_profile",
                            "manifest_field": "target.hardware_profile",
                            "manifest_value": target_hardware_profile,
                            "expected_value": expected_profile,
                        }
                    )

        outputs = self.manifest.get("outputs")
        if not isinstance(outputs, Mapping):
            diagnostics.append(self._missing_metadata_diagnostic("outputs.kernel_config"))
            diagnostics.append(self._missing_metadata_diagnostic("outputs.pto_codegen_index"))
            diagnostics.append(self._missing_metadata_diagnostic("outputs.toolchain_manifest"))
        else:
            kernel_config = outputs.get("kernel_config")
            codegen_index = outputs.get("pto_codegen_index")
            toolchain_manifest = outputs.get("toolchain_manifest")
            if not isinstance(kernel_config, str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.kernel_config"))
            elif kernel_config != DEFAULT_KERNEL_CONFIG:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                        "detail": "manifest.json outputs.kernel_config must use the canonical PTO artifact path.",
                        "manifest_field": "outputs.kernel_config",
                    }
                )
            if not isinstance(codegen_index, str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.pto_codegen_index"))
            elif codegen_index != DEFAULT_CODEGEN_INDEX:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                        "detail": "manifest.json outputs.pto_codegen_index must use the canonical PTO artifact path.",
                        "manifest_field": "outputs.pto_codegen_index",
                    }
                )
            if not isinstance(toolchain_manifest, str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.toolchain_manifest"))
            elif toolchain_manifest != DEFAULT_TOOLCHAIN_MANIFEST:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                        "detail": "manifest.json outputs.toolchain_manifest must use the canonical PTO artifact path.",
                        "manifest_field": "outputs.toolchain_manifest",
                    }
                )

        manifest_pto_extension = self._pto_extension()
        if manifest_pto_extension is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto"))
            return diagnostics

        if not isinstance(manifest_pto_extension.get("platform"), str):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.platform"))
        if not isinstance(manifest_pto_extension.get("kernel_project_dir"), str):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.kernel_project_dir"))
        if not isinstance(manifest_pto_extension.get("toolchain_manifest"), str):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.toolchain_manifest"))
        if not isinstance(manifest_pto_extension.get("pto_runtime_contract"), str):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.pto_runtime_contract"))
        elif (
            self.variant is not None
            and variant_is_valid
            and manifest_pto_extension.get("pto_runtime_contract") != self._expected_runtime_contract()
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                    "detail": "manifest.json extensions.pto.pto_runtime_contract does not match the PTO variant contract.",
                    "manifest_field": "extensions.pto.pto_runtime_contract",
                    "manifest_value": manifest_pto_extension.get("pto_runtime_contract"),
                    "expected_value": self._expected_runtime_contract(),
                }
            )
        if not isinstance(manifest_pto_extension.get("pto_isa_contract"), str):
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.pto_isa_contract"))
        elif (
            self.variant is not None
            and variant_is_valid
            and manifest_pto_extension.get("pto_isa_contract") != self._expected_isa_contract()
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                    "detail": "manifest.json extensions.pto.pto_isa_contract does not match the PTO variant contract.",
                    "manifest_field": "extensions.pto.pto_isa_contract",
                    "manifest_value": manifest_pto_extension.get("pto_isa_contract"),
                    "expected_value": self._expected_isa_contract(),
                }
            )
        if manifest_pto_extension.get("runtime_config") is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.runtime_config"))
        if manifest_pto_extension.get("orchestration_entry") is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.orchestration_entry"))
        return diagnostics

    def _validate_toolchain_manifest(
        self,
        *,
        toolchain_manifest: dict[str, Any],
        manifest_pto_extension: Mapping[str, Any],
        toolchain_manifest_path: str,
    ) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []

        if toolchain_manifest.get("backend") != self.backend:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                    "detail": "PTO toolchain manifest backend does not agree with manifest target.",
                    "field": "backend",
                    "manifest_field": "target.backend",
                    "toolchain_field": f"{toolchain_manifest_path}.backend",
                    "manifest_value": self.backend,
                    "toolchain_value": toolchain_manifest.get("backend"),
                }
            )
        if (
            toolchain_manifest.get("variant") != self.variant
            or toolchain_manifest.get("platform") != self.variant
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_METADATA_MISMATCH",
                    "detail": "PTO toolchain manifest variant/platform does not agree with manifest target.",
                    "field": "variant",
                    "manifest_field": "target.variant",
                    "toolchain_variant_field": f"{toolchain_manifest_path}.variant",
                    "toolchain_platform_field": f"{toolchain_manifest_path}.platform",
                    "manifest_value": self.variant,
                    "toolchain_variant_value": toolchain_manifest.get("variant"),
                    "toolchain_platform_value": toolchain_manifest.get("platform"),
                }
            )

        runtime_contract = manifest_pto_extension.get("pto_runtime_contract")
        if toolchain_manifest.get("pto_runtime_contract") != runtime_contract:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "build/toolchain.json pto_runtime_contract does not match manifest.json extensions.pto.pto_runtime_contract.",
                    "manifest_field": "extensions.pto.pto_runtime_contract",
                }
            )
        elif (
            self.variant is not None
            and toolchain_manifest.get("pto_runtime_contract") != self._expected_runtime_contract()
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "build/toolchain.json pto_runtime_contract does not match the PTO variant contract.",
                    "toolchain_field": f"{toolchain_manifest_path}.pto_runtime_contract",
                    "toolchain_value": toolchain_manifest.get("pto_runtime_contract"),
                    "expected_value": self._expected_runtime_contract(),
                }
            )
        runtime_name = manifest_pto_extension.get("runtime_config", {}).get("runtime")
        if toolchain_manifest.get("runtime_name") != runtime_name:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "build/toolchain.json runtime_name does not match manifest.json extensions.pto.runtime_config.runtime.",
                    "toolchain_field": f"{toolchain_manifest_path}.runtime_name",
                    "toolchain_value": toolchain_manifest.get("runtime_name"),
                    "manifest_field": "extensions.pto.runtime_config.runtime",
                    "manifest_value": runtime_name,
                }
            )
        derived_outputs = toolchain_manifest.get("derived_outputs")
        try:
            expected_outputs = pto_runtime_adapter.declared_outputs(self.package_dir, self.manifest)
        except Exception as exc:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": f"Unable to derive PTO build outputs from the package contract: {exc}",
                }
            )
            return diagnostics
        if derived_outputs != expected_outputs:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "build/toolchain.json derived_outputs does not match the PTO adapter contract.",
                    "toolchain_field": f"{toolchain_manifest_path}.derived_outputs",
                    "toolchain_value": derived_outputs,
                    "expected_value": expected_outputs,
                }
            )

        isa_contract = manifest_pto_extension.get("pto_isa_contract")
        if toolchain_manifest.get("pto_isa_contract") != isa_contract:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "build/toolchain.json pto_isa_contract does not match manifest.json extensions.pto.pto_isa_contract.",
                    "manifest_field": "extensions.pto.pto_isa_contract",
                }
            )
        elif (
            self.variant is not None
            and toolchain_manifest.get("pto_isa_contract") != self._expected_isa_contract()
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "build/toolchain.json pto_isa_contract does not match the PTO variant contract.",
                    "toolchain_field": f"{toolchain_manifest_path}.pto_isa_contract",
                    "toolchain_value": toolchain_manifest.get("pto_isa_contract"),
                    "expected_value": self._expected_isa_contract(),
                }
            )

        expected_compiler_contract = None if self.variant == "a2a3sim" else "cann:stub"
        if toolchain_manifest.get("compiler_contract") != expected_compiler_contract:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "build/toolchain.json compiler_contract does not match the PTO variant contract.",
                    "toolchain_field": f"{toolchain_manifest_path}.compiler_contract",
                    "expected_value": expected_compiler_contract,
                    "toolchain_value": toolchain_manifest.get("compiler_contract"),
                }
            )

        env_payload = toolchain_manifest.get("env")
        if (
            not isinstance(env_payload, Mapping)
            or not isinstance(env_payload.get("PTO_ISA_ROOT"), str)
            or not env_payload.get("PTO_ISA_ROOT")
        ):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": "build/toolchain.json env must be a mapping containing string PTO_ISA_ROOT.",
                }
            )

        compile_flags = toolchain_manifest.get("compile_flags")
        if not isinstance(compile_flags, list) or not all(isinstance(flag, str) for flag in compile_flags):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_TOOLCHAIN_MANIFEST",
                    "detail": "build/toolchain.json compile_flags must be a list of strings.",
                }
            )

        return diagnostics

    def _target_record(self) -> Mapping[str, Any]:
        target = self.manifest.get("target")
        if not isinstance(target, Mapping):
            return {}
        return target

    def _expected_runtime_contract(self) -> str:
        return "pto-runtime:dev"

    def _expected_isa_contract(self) -> str:
        return f"pto-isa:{self.variant}"

    def _has_valid_variant(self) -> bool:
        if self.variant is None:
            return False
        try:
            arch_for(self.variant)
        except ValueError:
            return False
        return True

    def _missing_metadata_diagnostic(self, field: str) -> dict[str, Any]:
        return {
            "code": "HTP.BINDINGS.PTO_MISSING_METADATA",
            "detail": f"manifest.json {field} is required for PTO packages.",
            "manifest_field": field,
        }


def _load_python_module(path: Path, *, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import PTO artifact module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _has_pto_contract(package_dir: Path, manifest: Mapping[str, Any]) -> bool:
    outputs = manifest.get("outputs")
    if isinstance(outputs, Mapping) and (
        isinstance(outputs.get("kernel_config"), str)
        or isinstance(outputs.get("pto_codegen_index"), str)
        or isinstance(outputs.get("toolchain_manifest"), str)
    ):
        return True

    extensions = manifest.get("extensions")
    if isinstance(extensions, Mapping) and isinstance(extensions.get("pto"), Mapping):
        return True

    return (package_dir / PTO_PROJECT_DIR).exists()


__all__ = ["PTOBinding"]
