from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from htp.backends.nvgpu.arch import arch_for
from htp.backends.nvgpu.emit import (
    NVGPU_CODEGEN_SCHEMA_ID,
    NVGPU_PROJECT_DIR,
    NVGPU_TOOLCHAIN_PATH,
    NVGPU_TOOLCHAIN_SCHEMA_ID,
)

from .base import ManifestBinding, ValidationResult

DEFAULT_CODEGEN_INDEX = (NVGPU_PROJECT_DIR / "nvgpu_codegen.json").as_posix()
DEFAULT_TOOLCHAIN_MANIFEST = NVGPU_TOOLCHAIN_PATH.as_posix()


class NVGPUBinding(ManifestBinding):
    def validate(self) -> ValidationResult:
        base_report = super().validate()
        missing_files = list(base_report.missing_files)
        diagnostics = [
            diagnostic
            for diagnostic in base_report.diagnostics
            if diagnostic.get("code") != "HTP.BINDINGS.MISSING_BACKEND"
        ]

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

    def _required_paths(self) -> tuple[str, str]:
        outputs = self.manifest.get("outputs")
        if isinstance(outputs, Mapping):
            return (
                str(outputs.get("nvgpu_codegen_index", DEFAULT_CODEGEN_INDEX)),
                str(outputs.get("toolchain_manifest", DEFAULT_TOOLCHAIN_MANIFEST)),
            )
        return (DEFAULT_CODEGEN_INDEX, DEFAULT_TOOLCHAIN_MANIFEST)

    def _validate_metadata(self) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
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
            if not isinstance(outputs.get("toolchain_manifest"), str):
                diagnostics.append(self._missing_metadata_diagnostic("outputs.toolchain_manifest"))

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
        try:
            codegen_index = json.loads((self.package_dir / codegen_index_path).read_text())
        except Exception as exc:
            return [{"code": "HTP.BINDINGS.NVGPU_INVALID_CODEGEN_INDEX", "detail": str(exc)}]
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
            return [{"code": "HTP.BINDINGS.NVGPU_INVALID_TOOLCHAIN_MANIFEST", "detail": str(exc)}]
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

        backend = codegen_index.get("backend")
        if backend != "nvgpu":
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
                    "detail": "Manifest target.backend does not match NV-GPU binding selection.",
                    "field": "backend",
                    "manifest_field": "target.backend",
                    "manifest_value": self.backend,
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

        target = self.manifest.get("target")
        target_hardware_profile = (
            target.get("hardware_profile") if isinstance(target, Mapping) else None
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

        extension = self._nvgpu_extension() or {}
        if extension.get("toolchain_manifest") != toolchain_manifest_path:
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

    @staticmethod
    def _missing_metadata_diagnostic(field: str) -> dict[str, Any]:
        return {
            "code": "HTP.BINDINGS.NVGPU_MISSING_METADATA",
            "detail": f"manifest.json {field} is required for NV-GPU packages.",
            "manifest_field": field,
        }


__all__ = ["NVGPUBinding"]
