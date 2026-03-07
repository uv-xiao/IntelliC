from __future__ import annotations

import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from htp.backends.pto.arch import arch_for
from htp.backends.pto.emit import PTO_PROJECT_DIR

from .base import BuildResult, ManifestBinding, ValidationResult

DEFAULT_KERNEL_CONFIG = (PTO_PROJECT_DIR / "kernel_config.py").as_posix()
DEFAULT_CODEGEN_INDEX = (PTO_PROJECT_DIR / "pto_codegen.json").as_posix()


class PTOBinding(ManifestBinding):
    def validate(self) -> ValidationResult:
        base_report = super().validate()
        missing_files = list(base_report.missing_files)
        diagnostics = list(base_report.diagnostics)
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

        has_missing_metadata = any(diagnostic.get("code") == "HTP.BINDINGS.PTO_MISSING_METADATA" for diagnostic in diagnostics)
        if self._should_enforce_pto_contract() and not missing_files and not has_missing_metadata:
            diagnostics.extend(self._validate_pto_contract(kernel_config_path=required_paths[0], codegen_index_path=required_paths[1]))

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
        built_outputs = [] if not validation.ok else list(self._required_paths())
        log_path = session._write_log(
            kind="build",
            stem=f"build_{self.backend}_{mode}",
            lines=(
                f"backend={self.backend}",
                f"mode={mode}",
                f"platform={self._platform_for_mode(mode)}",
                f"validated={validation.ok}",
                f"built_outputs={tuple(built_outputs)!r}",
            ),
        )
        return BuildResult(
            ok=validation.ok,
            mode=mode,
            built_outputs=built_outputs,
            log_paths=[log_path],
            diagnostics=validation.diagnostics,
        )

    def _validate_pto_contract(
        self,
        *,
        kernel_config_path: str,
        codegen_index_path: str,
    ) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []

        try:
            kernel_config = _load_python_module(self.package_dir / kernel_config_path, module_name="htp_pto_kernel_config")
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
            "function_name": index_orchestration.get("function_name") if isinstance(index_orchestration, Mapping) else None,
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

        codegen_backend = codegen_index.get("backend") if isinstance(codegen_index.get("backend"), str) else None
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
        codegen_variant = codegen_index.get("variant") if isinstance(codegen_index.get("variant"), str) else None
        kernel_platform = runtime_config.get("platform") if isinstance(runtime_config.get("platform"), str) else None
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

        manifest_runtime_config = manifest_pto_extension.get("runtime_config")
        if manifest_runtime_config is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.runtime_config"))
        else:
            expected_manifest_runtime_config = {
                key: value for key, value in dict(runtime_config).items() if key != "platform"
            }
            if not isinstance(manifest_runtime_config, Mapping) or dict(manifest_runtime_config) != expected_manifest_runtime_config:
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
        elif not isinstance(manifest_orchestration_entry, Mapping) or dict(manifest_orchestration_entry) != dict(orchestration):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                    "detail": "manifest.json extensions.pto.orchestration_entry does not match kernel_config.py ORCHESTRATION.",
                    "manifest_field": "extensions.pto.orchestration_entry",
                }
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
        if isinstance(orchestration_source, str) and not (self._project_dir() / orchestration_source).exists():
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.PTO_INVALID_KERNEL_CONFIG",
                    "detail": f"kernel_config.py references missing PTO source: {orchestration_source}",
                }
            )

        return diagnostics

    def _required_paths(self) -> tuple[str, str]:
        outputs = self.manifest.get("outputs")
        if not isinstance(outputs, Mapping):
            return DEFAULT_KERNEL_CONFIG, DEFAULT_CODEGEN_INDEX

        kernel_config = outputs.get("kernel_config")
        codegen_index = outputs.get("pto_codegen_index")
        return (
            kernel_config if isinstance(kernel_config, str) else DEFAULT_KERNEL_CONFIG,
            codegen_index if isinstance(codegen_index, str) else DEFAULT_CODEGEN_INDEX,
        )

    def _should_enforce_pto_contract(self) -> bool:
        if self.backend == "pto":
            return True

        outputs = self.manifest.get("outputs")
        if isinstance(outputs, Mapping) and (
            isinstance(outputs.get("kernel_config"), str) or isinstance(outputs.get("pto_codegen_index"), str)
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
        return "a2a3sim" if self.variant is None else self.variant

    def _validate_required_metadata(self, *, required_paths: tuple[str, str]) -> list[dict[str, Any]]:
        if not self._should_enforce_pto_contract():
            return []

        diagnostics: list[dict[str, Any]] = []
        target = self._target_record()
        if self.variant is None:
            diagnostics.append(self._missing_metadata_diagnostic("target.variant"))

        target_hardware_profile = target.get("hardware_profile") if isinstance(target.get("hardware_profile"), str) else None
        if target_hardware_profile is None:
            diagnostics.append(self._missing_metadata_diagnostic("target.hardware_profile"))
        elif self.variant is not None:
            expected_profile = arch_for(self.variant).hardware_profile
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
        else:
            kernel_config = outputs.get("kernel_config")
            codegen_index = outputs.get("pto_codegen_index")
            if not isinstance(kernel_config, str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.kernel_config"))
            elif kernel_config != required_paths[0]:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                        "detail": "manifest.json outputs.kernel_config does not match the PTO binding contract.",
                        "manifest_field": "outputs.kernel_config",
                    }
                )
            if not isinstance(codegen_index, str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.pto_codegen_index"))
            elif codegen_index != required_paths[1]:
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.PTO_ARTIFACT_MISMATCH",
                        "detail": "manifest.json outputs.pto_codegen_index does not match the PTO binding contract.",
                        "manifest_field": "outputs.pto_codegen_index",
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
        if manifest_pto_extension.get("runtime_config") is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.runtime_config"))
        if manifest_pto_extension.get("orchestration_entry") is None:
            diagnostics.append(self._missing_metadata_diagnostic("extensions.pto.orchestration_entry"))
        return diagnostics

    def _target_record(self) -> Mapping[str, Any]:
        target = self.manifest.get("target")
        if not isinstance(target, Mapping):
            return {}
        return target

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


__all__ = ["PTOBinding"]
