from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from htp.ir.module import PROGRAM_MODULE_SCHEMA_ID
from htp.schemas import (
    MANIFEST_SCHEMA_ID,
    REPLAY_STUBS_SCHEMA_ID,
)

PTO_CODEGEN_SCHEMA_ID = "htp.pto.codegen.v1"
PTO_TOOLCHAIN_SCHEMA_ID = "htp.pto.toolchain.v1"
NVGPU_CODEGEN_SCHEMA_ID = "htp.nvgpu.codegen.v1"
NVGPU_TOOLCHAIN_SCHEMA_ID = "htp.nvgpu.toolchain.v1"
AIE_CODEGEN_SCHEMA_ID = "htp.aie.codegen.v1"
AIE_TOOLCHAIN_SCHEMA_ID = "htp.aie.toolchain.v1"
CPU_REF_CODEGEN_SCHEMA_ID = "htp.cpu_ref.codegen.v1"
CPU_REF_TOOLCHAIN_SCHEMA_ID = "htp.cpu_ref.toolchain.v1"

CONTRACT_REFS = (
    "docs/design/artifacts_replay_debug.md",
    "docs/design/backends_and_extensions.md",
    "docs/design/artifacts_replay_debug.md",
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
    outputs = manifest.get("outputs")
    if isinstance(outputs, Mapping):
        for value in outputs.values():
            if isinstance(value, str):
                yield value
    for stage in _stage_graph(manifest):
        yield from _stage_contract_paths(stage)


def validation_diagnostics(
    manifest: Mapping[str, Any], missing_files: tuple[str, ...], package_dir: Path | str | None = None
) -> tuple[dict[str, str], ...]:
    diagnostics: list[dict[str, str]] = []
    if manifest.get("schema") != MANIFEST_SCHEMA_ID:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.INVALID_SCHEMA",
                "detail": f"manifest.json must declare schema {MANIFEST_SCHEMA_ID!r}.",
            }
        )
    backend, _variant = manifest_target(manifest)
    if backend is None:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.MISSING_BACKEND",
                "detail": "Manifest target.backend is required for binding selection.",
            }
        )
    diagnostics.extend(_manifest_shape_diagnostics(manifest))
    if package_dir is not None:
        diagnostics.extend(_sidecar_schema_diagnostics(package_dir, manifest, missing_files))
    for missing_path in missing_files:
        diagnostics.append(
            {
                "code": "HTP.BINDINGS.MISSING_CONTRACT_FILE",
                "detail": f"Missing required artifact path: {missing_path}",
                "artifact_ref": missing_path,
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
    for key in ("dir", "program", "stage", "state"):
        value = stage.get(key)
        if isinstance(value, str):
            yield value

    runnable_py = stage.get("runnable_py")
    if isinstance(runnable_py, Mapping):
        for key in ("program_py", "stubs"):
            value = runnable_py.get(key)
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


def _sidecar_schema_diagnostics(
    package_dir: Path | str, manifest: Mapping[str, Any], missing_files: tuple[str, ...]
) -> list[dict[str, str]]:
    root = Path(package_dir)
    missing = set(missing_files)
    diagnostics: list[dict[str, str]] = []
    for relpath, expected_schema in _iter_schema_paths(manifest):
        if relpath in missing or expected_schema is None:
            continue
        path = root / relpath
        try:
            payload = json.loads(path.read_text())
        except Exception as exc:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.MALFORMED_JSON",
                    "detail": f"{relpath} could not be decoded as JSON: {exc}",
                    "artifact_ref": relpath,
                }
            )
            continue
        if not isinstance(payload, Mapping):
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.INVALID_SCHEMA",
                    "detail": f"{relpath} must decode to a mapping with schema {expected_schema!r}.",
                    "artifact_ref": relpath,
                }
            )
            continue
        if payload.get("schema") != expected_schema:
            diagnostics.append(
                {
                    "code": "HTP.BINDINGS.INVALID_SCHEMA",
                    "detail": f"{relpath} must declare schema {expected_schema!r}.",
                    "artifact_ref": relpath,
                }
            )
    return diagnostics


def _iter_schema_paths(manifest: Mapping[str, Any]) -> Iterable[tuple[str, str | None]]:
    outputs = manifest.get("outputs")
    backend, _variant = manifest_target(manifest)
    if isinstance(outputs, Mapping):
        for field, schema in _output_schema_map(backend).items():
            relpath = outputs.get(field)
            if isinstance(relpath, str):
                yield relpath, schema
    for stage in _stage_graph(manifest):
        state_path = stage.get("state")
        if isinstance(state_path, str):
            yield state_path, PROGRAM_MODULE_SCHEMA_ID
        stage_summary = stage.get("stage")
        if isinstance(stage_summary, str):
            yield stage_summary, "htp.stage.v2"
        runnable_py = stage.get("runnable_py")
        if isinstance(runnable_py, Mapping):
            stubs = runnable_py.get("stubs")
            if isinstance(stubs, str):
                yield stubs, REPLAY_STUBS_SCHEMA_ID


def _output_schema_map(backend: str | None) -> dict[str, str]:
    if backend == "pto":
        return {
            "pto_codegen_index": PTO_CODEGEN_SCHEMA_ID,
            "toolchain_manifest": PTO_TOOLCHAIN_SCHEMA_ID,
        }
    if backend == "nvgpu":
        return {
            "nvgpu_codegen_index": NVGPU_CODEGEN_SCHEMA_ID,
            "toolchain_manifest": NVGPU_TOOLCHAIN_SCHEMA_ID,
        }
    if backend == "aie":
        return {
            "aie_codegen_index": AIE_CODEGEN_SCHEMA_ID,
            "toolchain_manifest": AIE_TOOLCHAIN_SCHEMA_ID,
        }
    if backend == "cpu_ref":
        return {
            "cpu_ref_codegen_index": CPU_REF_CODEGEN_SCHEMA_ID,
            "toolchain_manifest": CPU_REF_TOOLCHAIN_SCHEMA_ID,
        }
    return {}


__all__ = [
    "CONTRACT_REFS",
    "collect_missing_files",
    "iter_contract_paths",
    "load_manifest",
    "manifest_target",
    "validation_diagnostics",
]
