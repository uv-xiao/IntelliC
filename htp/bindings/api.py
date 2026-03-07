from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .base import ManifestBinding, binding_from_manifest
from .validate import load_manifest, manifest_target

BindingFactory = Callable[[Path, dict[str, Any]], ManifestBinding]


def bind(package_dir: Path | str, binding_override: BindingFactory | None = None) -> ManifestBinding:
    package_path = Path(package_dir)
    manifest = load_manifest(package_path)
    if binding_override is not None:
        return binding_override(package_path, manifest)

    backend, _variant = manifest_target(manifest)
    if backend is None:
        raise ValueError("Manifest target.backend is required for binding selection")

    return binding_from_manifest(package_path, manifest)


__all__ = ["BindingFactory", "bind"]
