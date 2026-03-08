from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from htp.backends.declarations import BackendSolverDeclaration
from htp.backends.nvgpu.declarations import declaration_for as nvgpu_declaration_for
from htp.backends.pto.declarations import declaration_for as pto_declaration_for
from htp.passes import (
    analyze_schedule,
    apply_schedule,
    ast_canonicalize,
    emit_package,
    semantic_model,
    typecheck_layout_effects,
)
from htp.passes.contracts import PassContract
from htp.passes.program_model import build_semantic_model, canonicalize_program, normalize_target

SOLVER_FAILURE_SCHEMA_ID = "htp.solver_failure.v1"
DEFAULT_TEMPLATE_ID = "htp.default.v1"


@dataclass(frozen=True)
class CapabilityState:
    capabilities: tuple[str, ...] = ()
    layout_invariants: tuple[str, ...] = ()
    effect_invariants: tuple[str, ...] = ()
    analyses: tuple[str, ...] = ()
    target: dict[str, str] = field(default_factory=dict)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_json(self) -> dict[str, Any]:
        return {
            "capabilities": list(self.capabilities),
            "layout_invariants": list(self.layout_invariants),
            "effect_invariants": list(self.effect_invariants),
            "analyses": list(self.analyses),
            "target": dict(self.target),
        }


@dataclass(frozen=True)
class PipelineTemplate:
    template_id: str
    passes: tuple[PassContract, ...]
    required_outputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SolverFailure:
    template_id: str
    failed_at_pass: str
    missing_caps: tuple[str, ...] = ()
    missing_handlers: tuple[dict[str, str], ...] = ()
    analysis_requirements: tuple[str, ...] = ()
    artifact_contract_violations: tuple[str, ...] = ()
    providers: tuple[dict[str, Any], ...] = ()
    hints: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SOLVER_FAILURE_SCHEMA_ID,
            "pipeline": self.template_id,
            "failed_at_pass": self.failed_at_pass,
            "missing_caps": list(self.missing_caps),
            "missing_handlers": [dict(item) for item in self.missing_handlers],
            "analysis_requirements": list(self.analysis_requirements),
            "artifact_contract_violations": list(self.artifact_contract_violations),
            "providers": [dict(item) for item in self.providers],
            "hints": list(self.hints),
        }


@dataclass(frozen=True)
class SolverResult:
    ok: bool
    template_id: str
    pass_ids: list[str]
    capabilities: tuple[str, ...]
    state: CapabilityState
    required_outputs: tuple[str, ...]
    extension_results: dict[str, dict[str, Any]]
    failure: SolverFailure | None = None


def default_pipeline_template(*, target: dict[str, str]) -> PipelineTemplate:
    declaration = _backend_declaration(target)
    return PipelineTemplate(
        template_id=DEFAULT_TEMPLATE_ID,
        passes=(
            ast_canonicalize.CONTRACT,
            semantic_model.CONTRACT,
            typecheck_layout_effects.CONTRACT,
            analyze_schedule.CONTRACT,
            apply_schedule.CONTRACT,
            emit_package.CONTRACT,
        ),
        required_outputs=declaration.required_outputs,
    )


def solve_default_pipeline(*, program: dict[str, Any]) -> SolverResult:
    target = normalize_target(program)
    template = default_pipeline_template(target=target)
    return solve_pipeline(program=program, template=template)


def solve_pipeline(
    *,
    program: dict[str, Any],
    template: PipelineTemplate,
) -> SolverResult:
    target = normalize_target(program)
    extension_results = _collect_extension_results(program)
    initial_capabilities = tuple(
        extension_capability
        for result in extension_results.values()
        for extension_capability in result["provides"]
    )
    declaration = _backend_declaration(target)
    state = CapabilityState(capabilities=initial_capabilities, target=target)
    if declaration.target_capabilities:
        state = CapabilityState(
            capabilities=tuple(dict.fromkeys((*declaration.target_capabilities, *initial_capabilities))),
            target=target,
        )

    handler_failure = _handler_failure(
        program, target=target, template=template, state=state, extension_results=extension_results
    )
    if handler_failure is not None:
        return handler_failure

    capabilities = set(initial_capabilities)
    layout_invariants: set[str] = set()
    effect_invariants: set[str] = set()
    analyses: set[str] = set()
    providers = {provided: contract.pass_id for contract in template.passes for provided in contract.provides}

    for contract in template.passes:
        missing_caps = tuple(
            dict.fromkeys(
                requirement
                for requirement in (*contract.requires, *contract.analysis_requires)
                if requirement not in capabilities and requirement not in analyses
            )
        )
        missing_layout = tuple(
            invariant
            for invariant in contract.requires_layout_invariants
            if invariant not in layout_invariants
        )
        missing_effects = tuple(
            invariant
            for invariant in contract.requires_effect_invariants
            if invariant not in effect_invariants
        )
        if missing_caps or missing_layout or missing_effects:
            failure = SolverFailure(
                template_id=template.template_id,
                failed_at_pass=contract.pass_id,
                missing_caps=missing_caps + missing_layout + missing_effects,
                analysis_requirements=tuple(contract.analysis_requires),
                providers=tuple(
                    {"capability": capability, "pass_id": providers[capability]}
                    for capability in missing_caps
                    if capability in providers
                ),
            )
            return SolverResult(
                ok=False,
                template_id=template.template_id,
                pass_ids=[pass_contract.pass_id for pass_contract in template.passes],
                capabilities=tuple(sorted(capabilities)),
                state=CapabilityState(
                    capabilities=tuple(sorted(capabilities)),
                    layout_invariants=tuple(sorted(layout_invariants)),
                    effect_invariants=tuple(sorted(effect_invariants)),
                    analyses=tuple(sorted(analyses)),
                    target=target,
                ),
                required_outputs=template.required_outputs,
                extension_results=extension_results,
                failure=failure,
            )

        capabilities.difference_update(contract.invalidates)
        analyses.difference_update(contract.invalidates)
        capabilities.update(contract.provides)
        capabilities.update(contract.establishes_layout_invariants)
        capabilities.update(contract.establishes_effect_invariants)
        analyses.update(contract.provides)
        analyses.update(output.analysis_id for output in contract.analysis_produces)
        layout_invariants.update(contract.establishes_layout_invariants)
        effect_invariants.update(contract.establishes_effect_invariants)

    final_state = CapabilityState(
        capabilities=tuple(sorted(capabilities)),
        layout_invariants=tuple(sorted(layout_invariants)),
        effect_invariants=tuple(sorted(effect_invariants)),
        analyses=tuple(sorted(analyses)),
        target=target,
    )
    return SolverResult(
        ok=True,
        template_id=template.template_id,
        pass_ids=[pass_contract.pass_id for pass_contract in template.passes],
        capabilities=final_state.capabilities,
        state=final_state,
        required_outputs=template.required_outputs,
        extension_results=extension_results,
    )


def validate_final_artifacts(package_dir: Path | str, result: SolverResult) -> SolverResult:
    package_path = Path(package_dir)
    missing_outputs = tuple(
        output for output in result.required_outputs if not (package_path / output).exists()
    )
    if not missing_outputs:
        return result
    failure = SolverFailure(
        template_id=result.template_id,
        failed_at_pass="final_contract",
        artifact_contract_violations=missing_outputs,
    )
    _write_solver_failure(package_path, failure)
    return SolverResult(
        ok=False,
        template_id=result.template_id,
        pass_ids=result.pass_ids,
        capabilities=result.capabilities,
        state=result.state,
        required_outputs=result.required_outputs,
        extension_results=result.extension_results,
        failure=failure,
    )


def _handler_failure(
    program: dict[str, Any],
    *,
    target: dict[str, str],
    template: PipelineTemplate,
    state: CapabilityState,
    extension_results: dict[str, dict[str, Any]],
) -> SolverResult | None:
    canonical_ast = canonicalize_program(program)
    kernel_ir, _workload_ir, _entities, _bindings = build_semantic_model(canonical_ast)
    backend = target["backend"]
    supported_ops = set(_backend_declaration(target).supported_ops)
    missing_handlers = tuple(
        {"backend": backend, "op": str(op["op"])}
        for op in kernel_ir.get("ops", ())
        if str(op.get("op")) not in supported_ops
    )
    if not missing_handlers:
        return None
    failure = SolverFailure(
        template_id=template.template_id,
        failed_at_pass="target.handlers",
        missing_handlers=missing_handlers,
    )
    return SolverResult(
        ok=False,
        template_id=template.template_id,
        pass_ids=[pass_contract.pass_id for pass_contract in template.passes],
        capabilities=state.capabilities,
        state=state,
        required_outputs=template.required_outputs,
        extension_results=extension_results,
        failure=failure,
    )


def _collect_extension_results(program: dict[str, Any]) -> dict[str, dict[str, Any]]:
    requested = program.get("extensions", {}).get("requested", ())
    results: dict[str, dict[str, Any]] = {}
    if "htp_ext.mlir_cse" in requested:
        from htp_ext.mlir_cse.export import eligibility_for

        eligibility = eligibility_for(program)
        results["htp_ext.mlir_cse"] = {
            "eligible": bool(eligibility["ok"]),
            "provides": ["Extension.MLIRCSEEligible@1"] if eligibility["ok"] else [],
            "reasons": list(eligibility["reasons"]),
        }
    return results


def _backend_declaration(target: dict[str, str]) -> BackendSolverDeclaration:
    backend = target["backend"]
    option = target.get("option")
    if backend == "pto":
        return pto_declaration_for(option)
    if backend == "nvgpu":
        return nvgpu_declaration_for(option)
    return BackendSolverDeclaration(
        backend=backend,
        variant=option or "default",
        hardware_profile=f"{backend}:{option or 'default'}",
        target_capabilities=(),
        supported_ops=("elementwise_binary", "matmul"),
        required_outputs=(),
    )


def _write_solver_failure(package_dir: Path, failure: SolverFailure) -> None:
    failure_path = package_dir / "ir" / "solver_failure.json"
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text(json.dumps(failure.to_json(), indent=2) + "\n")


__all__ = [
    "CapabilityState",
    "DEFAULT_TEMPLATE_ID",
    "PipelineTemplate",
    "SOLVER_FAILURE_SCHEMA_ID",
    "SolverFailure",
    "SolverResult",
    "default_pipeline_template",
    "solve_default_pipeline",
    "solve_pipeline",
    "validate_final_artifacts",
]
