from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

CONTRACT_REFS = (
    "docs/design/impls/07_binding_interface.md",
    "docs/design/feats/08_binding_runtime.md",
    "docs/design/impls/04_artifact_manifest.md",
)


def load_manifest(package_dir: Path | str) -> dict[str, Any]:
    manifest_path = Path(package_dir) / "manifest.json"
    return json.loads(manifest_path.read_text())


def manifest_target(manifest: Mapping[str, Any]) -> tuple[str | None, str | None]:
    target = manifest.get("target")
    if not isinstance(target, Mapping):
        return None, None
    backend = target.get("backend")
    variant = target.get("variant")
    return _as_optional_str(backend), _as_optional_str(variant)


def collect_missing_files(package_dir: Path | str, manifest: Mapping[str, Any]) -> tuple[str, ...]:
    root = Path(package_dir)
    missing_files = [path for path in iter_contract_paths(manifest) if not (root / path).exists()]
    return tuple(dict.fromkeys(missing_files))


def iter_contract_paths(manifest: Mapping[str, Any]) -> Iterable[str]:
    for stage in _stage_graph(manifest):
        yield from _stage_contract_paths(stage)


def validation_diagnostics(
    manifest: Mapping[str, Any], missing_files: tuple[str, ...]
) -> tuple[dict[str, str], ...]:
    diagnostics: list[dict[str, str]] = []
    backend, _variant = manifest_target(manifest)
    if backend is None:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.MISSING_BACKEND",
                "detail": "Manifest target.backend is required for binding selection.",
            }
        )
    diagnostics.extend(_manifest_shape_diagnostics(manifest))
    for missing_path in missing_files:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.MISSING_CONTRACT_FILE",
                "detail": f"Missing required artifact path: {missing_path}",
            }
        )
    return tuple(diagnostics)


def _stage_graph(manifest: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    stages = manifest.get("stages")
    if not isinstance(stages, Mapping):
        return ()
    graph = stages.get("graph")
    if not isinstance(graph, list):
        return ()
    return tuple(stage for stage in graph if isinstance(stage, Mapping))


def _stage_contract_paths(stage: Mapping[str, Any]) -> Iterable[str]:
    for key in ("dir", "analysis_index", "summary", "program_pyast"):
        value = stage.get(key)
        if isinstance(value, str):
            yield value

    semantic = stage.get("semantic")
    if isinstance(semantic, Mapping):
        for key in ("kernel_ir", "workload_ir", "types", "layout", "effects", "schedule"):
            value = semantic.get(key)
            if isinstance(value, str):
                yield value

    runnable_py = stage.get("runnable_py")
    if isinstance(runnable_py, Mapping):
        for key in ("program_py", "stubs"):
            value = runnable_py.get(key)
            if isinstance(value, str):
                yield value

    ids = stage.get("ids")
    if isinstance(ids, Mapping):
        for key in ("entities", "bindings"):
            value = ids.get(key)
            if isinstance(value, str):
                yield value
    islands = stage.get("islands")
    if isinstance(islands, list):
        for island in islands:
            if not isinstance(island, Mapping):
                continue
            value = island.get("dir")
            if isinstance(value, str):
                yield value

    maps = stage.get("maps")
    if isinstance(maps, Mapping):
        for key in ("entity_map", "binding_map"):
            value = maps.get(key)
            if isinstance(value, str):
                yield value


def _as_optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _manifest_shape_diagnostics(manifest: Mapping[str, Any]) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    inputs = manifest.get("inputs")
    if inputs is not None and not isinstance(inputs, Mapping):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.MALFORMED_MANIFEST_SECTION",
                "detail": "manifest.json inputs must be a mapping when present.",
            }
        )
    pipeline = manifest.get("pipeline")
    if pipeline is not None:
        if not isinstance(pipeline, Mapping):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.MALFORMED_MANIFEST_SECTION",
                    "detail": "manifest.json pipeline must be a mapping when present.",
                }
            )
        else:
            pass_ids = pipeline.get("pass_ids")
            if pass_ids is not None and (
                isinstance(pass_ids, (str, bytes)) or not isinstance(pass_ids, Iterable)
            ):
                diagnostics.append(
                    {
                        "code": "HTP.BINDINGS.MALFORMED_MANIFEST_SECTION",
                        "detail": "manifest.json pipeline.pass_ids must be a list of strings when present.",
                    }
                )
    capabilities = manifest.get("capabilities")
    if capabilities is not None and not isinstance(capabilities, Mapping):
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.MALFORMED_MANIFEST_SECTION",
                "detail": "manifest.json capabilities must be a mapping when present.",
            }
        )
    return diagnostics


__all__ = [
    "CONTRACT_REFS",
    "collect_missing_files",
    "iter_contract_paths",
    "load_manifest",
    "manifest_target",
    "validation_diagnostics",
]
