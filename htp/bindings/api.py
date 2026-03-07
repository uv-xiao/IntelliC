from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .base import ManifestBinding, binding_from_manifest
from .validate import load_manifest, manifest_target

BindingFactory = Callable[[Path, dict[str, Any]], ManifestBinding]


def bind(package_dir: Path | str, binding_override: BindingFactory | None = None) -> ManifestBinding:
    package_path = Path(package_dir)
    manifest = load_manifest(package_path)
    if binding_override is not None:
        return binding_override(package_path, manifest)

    backend, variant = manifest_target(manifest)
    outputs = manifest.get("outputs")
    extensions = manifest.get("extensions")

    if backend == "nvgpu":
        from .nvgpu import NVGPUBinding

        return NVGPUBinding(
            package_dir=package_path,
            manifest=manifest,
            backend="nvgpu",
            variant=variant,
        )
    if backend == "aie":
        from .aie import AIEBinding

        return AIEBinding(
            package_dir=package_path,
            manifest=manifest,
            backend="aie",
            variant=variant,
        )
    if backend == "pto":
        from .pto import PTOBinding

        return PTOBinding(
            package_dir=package_path,
            manifest=manifest,
            backend="pto",
            variant=variant,
        )

    has_nvgpu_markers = (
        (isinstance(outputs, dict) and "nvgpu_codegen_index" in outputs)
        or (isinstance(extensions, dict) and "nvgpu" in extensions)
        or (package_path / "codegen" / "nvgpu").exists()
    )
    if has_nvgpu_markers:
        from .nvgpu import NVGPUBinding

        return NVGPUBinding(
            package_dir=package_path,
            manifest=manifest,
            backend="nvgpu",
            variant="cuda" if variant is None else variant,
        )

    has_pto_markers = (
        (isinstance(outputs, dict) and any(key in outputs for key in ("kernel_config", "pto_codegen_index")))
        or (isinstance(extensions, dict) and "pto" in extensions)
        or (package_path / "codegen" / "pto").exists()
        or (package_path / "build" / "toolchain.json").exists()
    )
    if has_pto_markers:
        from .pto import PTOBinding

        return PTOBinding(
            package_dir=package_path,
            manifest=manifest,
            backend="pto",
            variant=variant,
        )

    has_aie_markers = (
        (isinstance(outputs, dict) and "aie_codegen_index" in outputs)
        or (isinstance(extensions, dict) and "aie" in extensions)
        or (package_path / "codegen" / "aie").exists()
    )
    if has_aie_markers:
        from .aie import AIEBinding

        return AIEBinding(
            package_dir=package_path,
            manifest=manifest,
            backend="aie",
            variant="mlir-aie" if variant is None else variant,
        )

    if backend is None:
        stages = manifest.get("stages")
        if isinstance(stages, dict) and isinstance(stages.get("graph"), list):
            return binding_from_manifest(
                package_path,
                {
                    **manifest,
                    "target": {
                        **(manifest.get("target") or {}),
                        "backend": "generic",
                    },
                },
            )
        raise ValueError("Manifest target.backend is required for binding selection")

    return binding_from_manifest(package_path, manifest)


__all__ = ["BindingFactory", "bind"]
