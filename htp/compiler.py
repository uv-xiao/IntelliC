from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from htp.bindings.api import bind
from htp.pipeline.defaults import DefaultPipelineResult, run_default_pipeline


@dataclass(frozen=True)
class TargetSpec:
    backend: str
    option: str | None


@dataclass(frozen=True)
class CompiledPackage:
    package_dir: Path
    target: TargetSpec
    manifest: dict[str, Any]
    pipeline: DefaultPipelineResult


def parse_target(target: str) -> TargetSpec:
    if not target or not isinstance(target, str):
        raise ValueError("target must be a non-empty string")
    backend, separator, option = target.partition("-")
    if backend not in {"pto", "nvgpu"}:
        raise ValueError(f"Unsupported target backend {backend!r}; expected one of: nvgpu, pto")
    return TargetSpec(backend=backend, option=(option if separator else None))


def compile_program(
    *,
    package_dir: str | Path,
    target: str,
    program: dict[str, Any] | None = None,
) -> CompiledPackage:
    target_spec = parse_target(target)
    package_path = Path(package_dir)
    pipeline_program = dict(program or {})
    pipeline_program.setdefault(
        "target",
        {
            "backend": target_spec.backend,
            "option": target_spec.option,
        },
    )
    pipeline_result = run_default_pipeline(
        package_dir=package_path,
        program=pipeline_program,
    )
    _emit_backend_package(
        package_dir=package_path,
        target_spec=target_spec,
        program=pipeline_result.program,
    )
    manifest = json.loads((package_path / "manifest.json").read_text())
    validation = bind(package_path).validate()
    if not validation.ok:
        codes = ", ".join(diagnostic["code"] for diagnostic in validation.diagnostics)
        raise RuntimeError(f"Compiled package failed validation for target {target!r}: {codes}")
    return CompiledPackage(
        package_dir=package_path,
        target=target_spec,
        manifest=manifest,
        pipeline=pipeline_result,
    )


def _emit_backend_package(*, package_dir: Path, target_spec: TargetSpec, program: dict[str, Any]) -> None:
    if target_spec.backend == "pto":
        from htp.backends.pto.emit import emit_package as emit_pto_package

        emit_pto_package(package_dir, program=program, variant=target_spec.option)
        return
    if target_spec.backend == "nvgpu":
        from htp.backends.nvgpu.emit import emit_package as emit_nvgpu_package

        emit_nvgpu_package(package_dir, program=program, profile=target_spec.option)
        return
    raise AssertionError(f"Unhandled target backend: {target_spec.backend}")


__all__ = ["CompiledPackage", "TargetSpec", "compile_program", "parse_target"]
