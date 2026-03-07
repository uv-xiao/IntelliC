from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.passes import (
    PassManager,
    PassResult,
    analyze_schedule,
    apply_schedule,
    ast_canonicalize,
    emit_package,
    semantic_model,
    typecheck_layout_effects,
)
from htp.passes.contracts import PassContract
from htp.passes.program_model import stage_payloads_from_program


@dataclass(frozen=True)
class _PipelinePass:
    contract: PassContract
    run: Callable[[Mapping[str, Any], Mapping[str, object]], tuple[dict[str, Any], PassResult]]


@dataclass(frozen=True)
class DefaultPipelineResult:
    package_dir: Path
    current_stage: str
    pass_ids: list[str]
    program: dict[str, Any]
    stages: list[dict[str, object]]


MANDATORY_PASSES = (
    _PipelinePass(contract=ast_canonicalize.CONTRACT, run=ast_canonicalize.run),
    _PipelinePass(contract=semantic_model.CONTRACT, run=semantic_model.run),
    _PipelinePass(contract=typecheck_layout_effects.CONTRACT, run=typecheck_layout_effects.run),
    _PipelinePass(contract=analyze_schedule.CONTRACT, run=analyze_schedule.run),
    _PipelinePass(contract=apply_schedule.CONTRACT, run=apply_schedule.run),
    _PipelinePass(contract=emit_package.CONTRACT, run=emit_package.run),
)
MANDATORY_PASS_IDS = tuple(pipeline_pass.contract.pass_id for pipeline_pass in MANDATORY_PASSES)


def run_default_pipeline(
    *,
    package_dir: str | Path,
    program: Mapping[str, Any] | None = None,
) -> DefaultPipelineResult:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)

    program_state = deepcopy(dict(program or _example_program()))
    initial_payloads = stage_payloads_from_program(program_state)
    initial_stage = write_stage(
        package_path,
        StageSpec(
            stage_id="s00",
            pass_id=None,
            runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
            program_ast_payload=initial_payloads["program_ast_payload"],
            kernel_ir_payload=initial_payloads["kernel_ir_payload"],
            workload_ir_payload=initial_payloads["workload_ir_payload"],
            types_payload=initial_payloads["types_payload"],
            layout_payload=initial_payloads["layout_payload"],
            effects_payload=initial_payloads["effects_payload"],
            schedule_payload=initial_payloads["schedule_payload"],
            entities_payload=initial_payloads["entities_payload"],
            bindings_payload=initial_payloads["bindings_payload"],
        ),
    )
    write_manifest(package_path, current_stage="s00", stages=[initial_stage])

    manager = PassManager(
        package_dir=package_path,
        stages=[initial_stage],
        current_stage="s00",
    )
    capabilities: set[str] = set()

    for pipeline_pass in MANDATORY_PASSES:
        _ensure_requires_satisfied(pipeline_pass.contract, capabilities)

        next_program: dict[str, Any] | None = None

        def execute(stage_before: dict[str, object]) -> PassResult:
            nonlocal next_program
            next_program, result = pipeline_pass.run(program_state, stage_before=stage_before)
            return result

        manager.run(pipeline_pass.contract, execute)
        if next_program is None:
            raise RuntimeError(f"Pass {pipeline_pass.contract.pass_id} did not produce program state")

        program_state = next_program
        capabilities.difference_update(pipeline_pass.contract.invalidates)
        capabilities.update(pipeline_pass.contract.provides)

    return DefaultPipelineResult(
        package_dir=package_path,
        current_stage=manager.current_stage,
        pass_ids=list(MANDATORY_PASS_IDS),
        program=program_state,
        stages=list(manager.stages),
    )


def _example_program() -> dict[str, Any]:
    return {
        "entry": "vector_add",
        "kernel": {
            "name": "vector_add",
            "args": [
                {"name": "lhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                {"name": "rhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                {"name": "out", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "output"},
                {"name": "size", "kind": "scalar", "dtype": "i32", "role": "shape"},
            ],
            "ops": [
                {
                    "op": "elementwise_binary",
                    "operator": "add",
                    "lhs": "lhs",
                    "rhs": "rhs",
                    "out": "out",
                    "shape": ["size"],
                    "dtype": "f32",
                }
            ],
        },
        "workload": {
            "entry": "vector_add",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "vector_add",
                    "args": ["lhs", "rhs", "out", "size"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
        "analysis": {},
        "package": {"emitted": False},
        "target": {"backend": "pto", "option": "a2a3sim"},
    }


def _ensure_requires_satisfied(contract: PassContract, capabilities: set[str]) -> None:
    missing = [requirement for requirement in contract.requires if requirement not in capabilities]
    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(f"Pass {contract.pass_id} is missing required capabilities: {missing_list}")


__all__ = [
    "DefaultPipelineResult",
    "MANDATORY_PASS_IDS",
    "MANDATORY_PASSES",
    "run_default_pipeline",
]
