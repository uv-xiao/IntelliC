from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.compiler_errors import CompilerDiagnosticError, failure_payload
from htp.passes import PassManager, PassResult
from htp.passes.contracts import PassContract
from htp.passes.program_model import stage_payloads_from_program
from htp.passes.registry import RegisteredPass, core_passes, resolve_passes
from htp.solver import (
    apply_contract_to_state,
    build_initial_capability_state,
    describe_state_delta,
    evaluate_contract_satisfaction,
    solve_default_pipeline,
)


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


MANDATORY_PASSES = tuple(_PipelinePass(contract=item.contract, run=item.run) for item in core_passes())
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
    solver_result = solve_default_pipeline(program=program_state)
    if not solver_result.ok:
        failure_path = package_path / "ir" / "solver_failure.json"
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        failure_path.write_text(json.dumps(solver_result.failure.to_json(), indent=2) + "\n")
        raise RuntimeError(f"Default pipeline is unsatisfied: {solver_result.failure.to_json()}")
    capability_state = build_initial_capability_state(
        program=program_state,
        extension_results=solver_result.extension_results,
    )
    selected_passes = tuple(
        _to_pipeline_pass(item) for item in resolve_passes(solver_result.pass_ids, program=program_state)
    )

    for pipeline_pass in selected_passes:
        next_program: dict[str, Any] | None = None
        satisfaction = evaluate_contract_satisfaction(
            contract=pipeline_pass.contract,
            state=capability_state,
        )
        if satisfaction.missing_caps or satisfaction.missing_layout or satisfaction.missing_effects:
            raise RuntimeError(
                f"Default pipeline contract drift at {pipeline_pass.contract.pass_id}: "
                f"{satisfaction.requires_satisfied}"
            )

        def execute(stage_before: dict[str, object]) -> PassResult:
            nonlocal next_program
            next_program, result = pipeline_pass.run(program_state, stage_before=stage_before)
            return result

        next_state = apply_contract_to_state(
            contract=pipeline_pass.contract,
            state=capability_state,
        )

        try:
            manager.run(
                pipeline_pass.contract,
                execute,
                requires_satisfied=satisfaction.requires_satisfied,
                state_delta=describe_state_delta(before=capability_state, after=next_state),
            )
        except CompilerDiagnosticError as exc:
            _write_compiler_failure(
                package_path,
                pass_id=pipeline_pass.contract.pass_id,
                stage_before=manager.current_stage,
                diagnostic=exc,
            )
            raise RuntimeError(
                f"Compiler failed at {pipeline_pass.contract.pass_id}: {exc.to_json()}"
            ) from None
        if next_program is None:
            raise RuntimeError(f"Pass {pipeline_pass.contract.pass_id} did not produce program state")

        program_state = next_program
        capability_state = next_state

    return DefaultPipelineResult(
        package_dir=package_path,
        current_stage=manager.current_stage,
        pass_ids=list(solver_result.pass_ids),
        program=program_state,
        stages=list(manager.stages),
    )


def _to_pipeline_pass(item: RegisteredPass) -> _PipelinePass:
    return _PipelinePass(contract=item.contract, run=item.run)


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


def _write_compiler_failure(
    package_dir: Path,
    *,
    pass_id: str,
    stage_before: str,
    diagnostic: CompilerDiagnosticError,
) -> None:
    failure_path = package_dir / "ir" / "compiler_failure.json"
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text(
        json.dumps(
            failure_payload(
                pass_id=pass_id,
                stage_before=stage_before,
                diagnostic=diagnostic,
            ),
            indent=2,
        )
        + "\n"
    )


__all__ = [
    "DefaultPipelineResult",
    "MANDATORY_PASS_IDS",
    "MANDATORY_PASSES",
    "run_default_pipeline",
]
