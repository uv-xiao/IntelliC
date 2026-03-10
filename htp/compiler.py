from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from htp.bindings.api import bind
from htp.pipeline.defaults import DefaultPipelineResult, run_default_pipeline
from htp.solver import solve_default_pipeline, validate_final_artifacts


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


class ProgramSurface(Protocol):
    def to_program(self) -> dict[str, Any]: ...


def parse_target(target: str) -> TargetSpec:
    if not target or not isinstance(target, str):
        raise ValueError("target must be a non-empty string")
    backend, separator, option = target.partition("-")
    if backend not in {"pto", "nvgpu", "aie", "cpu_ref"}:
        raise ValueError(f"Unsupported target backend {backend!r}; expected one of: aie, cpu_ref, nvgpu, pto")
    return TargetSpec(backend=backend, option=(option if separator else None))


def compile_program(
    *,
    package_dir: str | Path,
    target: str,
    program: dict[str, Any] | ProgramSurface | None = None,
) -> CompiledPackage:
    target_spec = parse_target(target)
    package_path = Path(package_dir)
    pipeline_program = _normalize_program_input(program)
    target_payload = pipeline_program.get("target")
    if not isinstance(target_payload, dict) or not target_payload:
        target_payload = {}
    target_payload.setdefault("backend", target_spec.backend)
    target_payload.setdefault("option", target_spec.option)
    pipeline_program["target"] = target_payload
    package_path.mkdir(parents=True, exist_ok=True)
    solver_result = solve_default_pipeline(program=pipeline_program)
    if not solver_result.ok:
        _write_solver_failure(package_path, solver_result)
        raise RuntimeError(f"Solver failed for target {target!r}: {solver_result.failure.to_json()}")
    pipeline_result = run_default_pipeline(
        package_dir=package_path,
        program=pipeline_program,
    )
    _emit_backend_package(
        package_dir=package_path,
        target_spec=target_spec,
        program=pipeline_result.program,
    )
    artifact_check = validate_final_artifacts(package_path, solver_result)
    if not artifact_check.ok:
        raise RuntimeError(
            f"Solver final artifact check failed for target {target!r}: {artifact_check.failure.to_json()}"
        )
    manifest = json.loads((package_path / "manifest.json").read_text())
    manifest = _enrich_manifest(
        manifest,
        target_spec=target_spec,
        pipeline_result=pipeline_result,
        solver_result=solver_result,
        program=pipeline_program,
    )
    (package_path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
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


def _normalize_program_input(program: dict[str, Any] | ProgramSurface | None) -> dict[str, Any]:
    if program is None:
        return {}
    if isinstance(program, dict):
        return dict(program)
    to_program = getattr(program, "to_program", None)
    if callable(to_program):
        payload = to_program()
        if not isinstance(payload, dict):
            raise TypeError("program.to_program() must return a dict payload")
        return dict(payload)
    raise TypeError("program must be a dict or expose to_program()")


def _write_solver_failure(package_dir: Path, solver_result: object) -> None:
    from htp.solver import SolverResult

    if not isinstance(solver_result, SolverResult) or solver_result.failure is None:
        return
    failure_path = package_dir / "ir" / "solver_failure.json"
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text(json.dumps(solver_result.failure.to_json(), indent=2) + "\n")


def _emit_backend_package(*, package_dir: Path, target_spec: TargetSpec, program: dict[str, Any]) -> None:
    if target_spec.backend == "pto":
        from htp.backends.pto.emit import emit_package as emit_pto_package

        emit_pto_package(package_dir, program=program, variant=target_spec.option)
        return
    if target_spec.backend == "nvgpu":
        from htp.backends.nvgpu.emit import emit_package as emit_nvgpu_package

        emit_nvgpu_package(package_dir, program=program, profile=target_spec.option)
        return
    if target_spec.backend == "aie":
        from htp_ext.aie.emit import emit_package as emit_aie_package

        emit_aie_package(package_dir, program=program, profile=target_spec.option or "xdna2-npu1")
        return
    if target_spec.backend == "cpu_ref":
        from htp_ext.cpu_ref.emit import emit_package as emit_cpu_ref_package

        emit_cpu_ref_package(package_dir, program=program)
        return
    raise AssertionError(f"Unhandled target backend: {target_spec.backend}")


def _enrich_manifest(
    manifest: dict[str, Any],
    *,
    target_spec: TargetSpec,
    pipeline_result: DefaultPipelineResult,
    solver_result: object,
    program: dict[str, Any],
) -> dict[str, Any]:
    from htp.solver import SolverResult

    next_manifest = dict(manifest)
    next_manifest["inputs"] = {
        "entry": str(program.get("entry", "")),
        "kernel_name": str(program.get("kernel", {}).get("name", ""))
        if isinstance(program.get("kernel"), dict)
        else "",
        "workload_entry": str(program.get("workload", {}).get("entry", ""))
        if isinstance(program.get("workload"), dict)
        else "",
        "requested_extensions": list(program.get("extensions", {}).get("requested", ()))
        if isinstance(program.get("extensions"), dict)
        else [],
    }
    if isinstance(solver_result, SolverResult):
        next_manifest["pipeline"] = {
            "template_id": solver_result.template_id,
            "pass_ids": list(pipeline_result.pass_ids),
            "current_stage": pipeline_result.current_stage,
        }
        next_manifest["capabilities"] = solver_result.state.to_json()
    next_manifest.setdefault("target", {})
    next_manifest["target"].setdefault("backend", target_spec.backend)
    if target_spec.option is not None:
        next_manifest["target"].setdefault("option", target_spec.option)
    return next_manifest


__all__ = ["CompiledPackage", "TargetSpec", "compile_program", "parse_target"]
