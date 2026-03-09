from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import ManifestBinding, ValidationResult

_REQUIRED_PATHS = (
    "codegen/aie/aie.mlir",
    "codegen/aie/mapping.json",
    "codegen/aie/fifos.json",
    "codegen/aie/host.py",
    "codegen/aie/aie_codegen.json",
    "codegen/aie/toolchain.json",
)


class AIEBinding(ManifestBinding):
    def validate(self) -> ValidationResult:
        base_report = super().validate()
        missing_files = list(base_report.missing_files)
        diagnostics = [
            diagnostic
            for diagnostic in base_report.diagnostics
            if diagnostic.get("code") != "HTP.BINDINGS.MISSING_BACKEND"
        ]
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
        return ValidationResult(
            ok=not diagnostics,
            backend=self.backend,
            variant=self.variant,
            diagnostics=diagnostics,
            missing_files=missing_files,
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
    return diagnostics


__all__ = ["AIEBinding"]
