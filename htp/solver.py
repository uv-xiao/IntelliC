from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from htp.backends.declarations import ArtifactContract, BackendSolverDeclaration
from htp.backends.nvgpu.declarations import declaration_for as nvgpu_declaration_for
from htp.backends.pto.declarations import declaration_for as pto_declaration_for
from htp.bindings.validate import load_manifest
from htp.passes.contracts import PassContract
from htp.passes.program_model import build_semantic_model, canonicalize_program, normalize_target
from htp.pipeline.registry import registered_templates
from htp_ext.registry import extension_results as registered_extension_results
from htp_ext.registry import requested_extension_ids

SOLVER_FAILURE_SCHEMA_ID = "htp.solver_failure.v1"
DEFAULT_TEMPLATE_ID = "htp.default.v1"
RESUME_TEMPLATE_ID = "htp.resume.v1"


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
    selection_cost: int = 0
    extension_steps: tuple[str, ...] = ()
    pass_choices: tuple[tuple[PassContract, ...], ...] = ()


@dataclass(frozen=True)
class SolverFailure:
    template_id: str
    failed_at_pass: str
    missing_caps: tuple[str, ...] = ()
    missing_handlers: tuple[dict[str, str], ...] = ()
    analysis_requirements: tuple[str, ...] = ()
    artifact_contract_violations: tuple[str, ...] = ()
    requested_extensions: tuple[str, ...] = ()
    extension_requirements: tuple[dict[str, Any], ...] = ()
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
            "requested_extensions": list(self.requested_extensions),
            "extension_requirements": [dict(item) for item in self.extension_requirements],
            "providers": [dict(item) for item in self.providers],
            "hints": list(self.hints),
        }


@dataclass(frozen=True)
class SolverResult:
    ok: bool
    template_id: str
    pass_ids: list[str]
    passes: tuple[PassContract, ...]
    selection_cost: int
    capabilities: tuple[str, ...]
    state: CapabilityState
    required_outputs: tuple[str, ...]
    extension_results: dict[str, dict[str, Any]]
    selection_trace: dict[str, int] = field(default_factory=dict)
    failure: SolverFailure | None = None


@dataclass(frozen=True)
class ContractSatisfaction:
    missing_caps: tuple[str, ...]
    missing_layout: tuple[str, ...]
    missing_effects: tuple[str, ...]
    requires_satisfied: dict[str, dict[str, bool]]


def default_pipeline_template(*, target: dict[str, str]) -> PipelineTemplate:
    declaration = _backend_declaration(target)
    return registered_templates(program={"target": target}, required_outputs=declaration.required_outputs)[0]


def available_pipeline_templates(*, program: dict[str, Any]) -> tuple[PipelineTemplate, ...]:
    target = normalize_target(program)
    templates = registered_templates(
        program=program, required_outputs=_backend_declaration(target).required_outputs
    )
    expanded: list[PipelineTemplate] = []
    for template in templates:
        expanded.extend(_expand_template_choices(template))
    return tuple(expanded)


def solve_default_pipeline(
    *,
    program: dict[str, Any],
    existing_package_dir: Path | str | None = None,
) -> SolverResult:
    extension_results = _collect_extension_results(program)
    requested_extensions = tuple(requested_extension_ids(program))
    templates = list(available_pipeline_templates(program=program))
    attempts: list[SolverResult] = []
    resume_attempt = _resume_attempt(
        program=program,
        existing_package_dir=existing_package_dir,
        requested_extensions=requested_extensions,
    )
    if resume_attempt is not None:
        attempts.append(_decorate_selection_trace(resume_attempt, requested_extensions=requested_extensions))
    for template in templates:
        result = solve_pipeline(program=program, template=template)
        attempts.append(_decorate_selection_trace(result, requested_extensions=requested_extensions))
    matching_attempts = [
        result
        for result in attempts
        if _template_satisfies_requested_extensions(result, requested_extensions=requested_extensions)
    ]
    successful = [result for result in matching_attempts if result.ok]
    if successful:
        return min(successful, key=_result_selection_key)
    if matching_attempts:
        return min(matching_attempts, key=_result_selection_key)
    requested_failure = _requested_extension_failure(
        requested_extensions=requested_extensions,
        extension_results=extension_results,
        attempts=attempts,
    )
    if requested_failure is not None:
        return requested_failure
    return attempts[-1]


def solve_pipeline(
    *,
    program: dict[str, Any],
    template: PipelineTemplate,
) -> SolverResult:
    target = normalize_target(program)
    extension_results = _collect_extension_results(program)
    state = build_initial_capability_state(program=program, extension_results=extension_results)
    if template.extension_steps:
        state = CapabilityState(
            capabilities=tuple(sorted({*state.capabilities, *template.extension_steps})),
            layout_invariants=state.layout_invariants,
            effect_invariants=state.effect_invariants,
            analyses=state.analyses,
            target=state.target,
        )

    handler_failure = _handler_failure(
        program, target=target, template=template, state=state, extension_results=extension_results
    )
    if handler_failure is not None:
        return handler_failure

    providers = {provided: contract.pass_id for contract in template.passes for provided in contract.provides}
    providers.update(
        {
            provided: extension_id
            for extension_id, result in extension_results.items()
            for provided in result.get("provides", ())
        }
    )

    for contract in template.passes:
        satisfaction = evaluate_contract_satisfaction(contract=contract, state=state)
        if satisfaction.missing_caps or satisfaction.missing_layout or satisfaction.missing_effects:
            failure = SolverFailure(
                template_id=template.template_id,
                failed_at_pass=contract.pass_id,
                missing_caps=(
                    satisfaction.missing_caps + satisfaction.missing_layout + satisfaction.missing_effects
                ),
                analysis_requirements=tuple(contract.analysis_requires),
                providers=tuple(
                    {"capability": capability, "pass_id": providers[capability]}
                    for capability in satisfaction.missing_caps
                    if capability in providers
                ),
            )
            return SolverResult(
                ok=False,
                template_id=template.template_id,
                pass_ids=[pass_contract.pass_id for pass_contract in template.passes],
                passes=template.passes,
                selection_cost=template.selection_cost,
                capabilities=state.capabilities,
                state=state,
                required_outputs=template.required_outputs,
                extension_results=extension_results,
                failure=failure,
            )

        state = apply_contract_to_state(contract=contract, state=state)
    required_outputs = _resolve_required_outputs(
        template=template,
        extension_results=extension_results,
    )
    return SolverResult(
        ok=True,
        template_id=template.template_id,
        pass_ids=[pass_contract.pass_id for pass_contract in template.passes],
        passes=template.passes,
        selection_cost=template.selection_cost,
        capabilities=state.capabilities,
        state=state,
        required_outputs=required_outputs,
        extension_results=extension_results,
    )


def validate_final_artifacts(package_dir: Path | str, result: SolverResult) -> SolverResult:
    package_path = Path(package_dir)
    manifest_outputs = _manifest_outputs(package_path)
    expected_outputs = manifest_outputs or result.required_outputs
    missing_outputs = tuple(output for output in expected_outputs if not (package_path / output).exists())
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
        passes=result.passes,
        selection_cost=result.selection_cost,
        capabilities=result.capabilities,
        state=result.state,
        required_outputs=result.required_outputs,
        extension_results=result.extension_results,
        failure=failure,
    )


def _resume_attempt(
    *,
    program: dict[str, Any],
    existing_package_dir: Path | str | None,
    requested_extensions: tuple[str, ...],
) -> SolverResult | None:
    if existing_package_dir is None:
        return None
    package_path = Path(existing_package_dir)
    if not package_path.exists():
        return None
    manifest = load_manifest(package_path)
    manifest_target = _manifest_target(manifest)
    requested_target = normalize_target(program)
    if manifest_target != requested_target:
        return None
    manifest_inputs = manifest.get("inputs", {})
    if isinstance(manifest_inputs, dict):
        current_inputs = _program_identity(program)
        if any(
            manifest_inputs.get(key) not in (None, current_inputs[key])
            for key in ("entry", "kernel_name", "workload_entry")
        ):
            return None
        existing_requested = tuple(manifest_inputs.get("requested_extensions", ()))
        if requested_extensions and tuple(existing_requested) != requested_extensions:
            return None
    resume_result = solve_existing_package(package_path)
    expected_outputs = set(_backend_declaration(requested_target).required_outputs)
    if not expected_outputs.issubset(set(resume_result.required_outputs)):
        return None
    return replace(
        resume_result,
        pass_ids=[],
        passes=(),
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
        passes=template.passes,
        selection_cost=template.selection_cost,
        capabilities=state.capabilities,
        state=state,
        required_outputs=template.required_outputs,
        extension_results=extension_results,
        failure=failure,
    )


def _collect_extension_results(program: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return registered_extension_results(program)


def build_initial_capability_state(
    *,
    program: dict[str, Any],
    extension_results: dict[str, dict[str, Any]] | None = None,
) -> CapabilityState:
    target = normalize_target(program)
    results = _collect_extension_results(program) if extension_results is None else extension_results
    extension_capabilities = tuple(
        extension_capability for result in results.values() for extension_capability in result["provides"]
    )
    declaration = _backend_declaration(target)
    capabilities = tuple(dict.fromkeys((*declaration.target_capabilities, *extension_capabilities)))
    return CapabilityState(capabilities=capabilities, target=target)


def evaluate_contract_satisfaction(
    *,
    contract: PassContract,
    state: CapabilityState,
) -> ContractSatisfaction:
    requires_status = {
        requirement: requirement in state.capabilities or requirement in state.analyses
        for requirement in contract.requires
    }
    analysis_requires_status = {
        requirement: requirement in state.analyses for requirement in contract.analysis_requires
    }
    layout_status = {
        invariant: invariant in state.layout_invariants for invariant in contract.requires_layout_invariants
    }
    effect_status = {
        invariant: invariant in state.effect_invariants for invariant in contract.requires_effect_invariants
    }
    return ContractSatisfaction(
        missing_caps=tuple(
            dict.fromkeys(
                requirement
                for requirement, satisfied in (*requires_status.items(), *analysis_requires_status.items())
                if not satisfied
            )
        ),
        missing_layout=tuple(invariant for invariant, satisfied in layout_status.items() if not satisfied),
        missing_effects=tuple(invariant for invariant, satisfied in effect_status.items() if not satisfied),
        requires_satisfied={
            "requires": requires_status,
            "analysis_requires": analysis_requires_status,
            "layout_invariants": layout_status,
            "effect_invariants": effect_status,
        },
    )


def apply_contract_to_state(*, contract: PassContract, state: CapabilityState) -> CapabilityState:
    capabilities = set(state.capabilities)
    analyses = set(state.analyses)
    layout_invariants = set(state.layout_invariants)
    effect_invariants = set(state.effect_invariants)

    capabilities.difference_update(contract.invalidates)
    analyses.difference_update(contract.invalidates)
    capabilities.update(contract.provides)
    capabilities.update(contract.establishes_layout_invariants)
    capabilities.update(contract.establishes_effect_invariants)
    analyses.update(contract.provides)
    analyses.update(output.analysis_id for output in contract.analysis_produces)
    layout_invariants.update(contract.establishes_layout_invariants)
    effect_invariants.update(contract.establishes_effect_invariants)

    return CapabilityState(
        capabilities=tuple(sorted(capabilities)),
        layout_invariants=tuple(sorted(layout_invariants)),
        effect_invariants=tuple(sorted(effect_invariants)),
        analyses=tuple(sorted(analyses)),
        target=state.target,
    )


def describe_state_delta(
    *,
    before: CapabilityState,
    after: CapabilityState,
) -> dict[str, list[str]]:
    before_caps = set(before.capabilities)
    after_caps = set(after.capabilities)
    before_analyses = set(before.analyses)
    after_analyses = set(after.analyses)
    before_layout = set(before.layout_invariants)
    after_layout = set(after.layout_invariants)
    before_effects = set(before.effect_invariants)
    after_effects = set(after.effect_invariants)
    return {
        "provides": sorted(after_caps - before_caps),
        "invalidates": sorted(before_caps - after_caps),
        "preserved_capabilities": sorted(before_caps & after_caps),
        "added_analyses": sorted(after_analyses - before_analyses),
        "removed_analyses": sorted(before_analyses - after_analyses),
        "preserved_analyses": sorted(before_analyses & after_analyses),
        "added_layout_invariants": sorted(after_layout - before_layout),
        "removed_layout_invariants": sorted(before_layout - after_layout),
        "preserved_layout_invariants": sorted(before_layout & after_layout),
        "added_effect_invariants": sorted(after_effects - before_effects),
        "removed_effect_invariants": sorted(before_effects - after_effects),
        "preserved_effect_invariants": sorted(before_effects & after_effects),
    }


def _backend_declaration(target: dict[str, str]) -> BackendSolverDeclaration:
    backend = target["backend"]
    option = target.get("option")
    if backend == "pto":
        return pto_declaration_for(option)
    if backend == "nvgpu":
        return nvgpu_declaration_for(option)
    if backend == "aie":
        from htp_ext.aie.declarations import declaration_for as aie_declaration_for

        return aie_declaration_for(option)
    return BackendSolverDeclaration(
        backend=backend,
        variant=option or "default",
        hardware_profile=f"{backend}:{option or 'default'}",
        target_capabilities=(),
        supported_ops=("elementwise_binary", "matmul"),
        artifact_contract=ArtifactContract(outputs=()),
    )


def _expand_template_choices(template: PipelineTemplate) -> tuple[PipelineTemplate, ...]:
    if not template.pass_choices:
        return (template,)
    templates = [template]
    for choice_index, alternatives in enumerate(template.pass_choices):
        next_templates: list[PipelineTemplate] = []
        for candidate in templates:
            for alternative in alternatives:
                next_templates.append(
                    PipelineTemplate(
                        template_id=f"{candidate.template_id}+choice{choice_index}:{alternative.pass_id}",
                        passes=candidate.passes + (alternative,),
                        required_outputs=candidate.required_outputs,
                        selection_cost=candidate.selection_cost,
                        extension_steps=candidate.extension_steps,
                    )
                )
        templates = next_templates
    return tuple(templates)


def _resolve_required_outputs(
    *,
    template: PipelineTemplate,
    extension_results: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    outputs = list(template.required_outputs)
    for extension_id in template.extension_steps:
        extension_output_paths = extension_results.get(extension_id, {}).get("required_outputs", ())
        for output in extension_output_paths:
            if isinstance(output, str):
                outputs.append(output)
    return tuple(dict.fromkeys(outputs))


def _result_selection_key(result: SolverResult) -> tuple[int, int, int, str]:
    total_cost = result.selection_trace.get("total", result.selection_cost)
    return (
        total_cost,
        sum(contract.deterministic is False for contract in result.passes) * 1000
        + sum(getattr(contract, "owner", "") != "htp" for contract in result.passes) * 100
        + len(result.passes) * 10
        + len(_template_extensions(result.template_id, result.extension_results)) * 5
        + len(result.required_outputs),
        len(result.passes),
        len(result.required_outputs),
        result.template_id,
    )


def _template_satisfies_requested_extensions(
    result: SolverResult,
    *,
    requested_extensions: tuple[str, ...],
) -> bool:
    if not requested_extensions:
        return True
    if result.template_id == RESUME_TEMPLATE_ID:
        return set(requested_extensions).issubset(set(result.extension_results))
    return set(requested_extensions).issubset(
        set(_template_extensions(result.template_id, result.extension_results))
    )


def _template_extensions(template_id: str, extension_results: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    extensions: list[str] = []
    for extension_id, payload in extension_results.items():
        templates = payload.get("pipeline_templates", ())
        if isinstance(templates, list | tuple) and template_id in templates:
            extensions.append(str(extension_id))
    return tuple(extensions)


def _decorate_selection_trace(
    result: SolverResult,
    *,
    requested_extensions: tuple[str, ...],
) -> SolverResult:
    matched_extensions = len(
        set(requested_extensions).intersection(
            set(_template_extensions(result.template_id, result.extension_results))
        )
    )
    if result.template_id == RESUME_TEMPLATE_ID:
        matched_extensions = len(set(requested_extensions).intersection(set(result.extension_results)))
    trace = {
        "base_cost": result.selection_cost,
        "pass_cost": len(result.passes) * 10,
        "extension_cost": len(_template_extensions(result.template_id, result.extension_results)) * 5,
        "output_cost": len(result.required_outputs),
        "resume_bonus": -200 if result.template_id == RESUME_TEMPLATE_ID else 0,
        "requested_extension_bonus": -(matched_extensions * 25),
    }
    trace["total"] = sum(trace.values())
    return replace(result, selection_trace=trace)


def _requested_extension_failure(
    *,
    requested_extensions: tuple[str, ...],
    extension_results: dict[str, dict[str, Any]],
    attempts: list[SolverResult],
) -> SolverResult | None:
    if not requested_extensions:
        return None
    extension_requirements = []
    hints: list[str] = []
    for extension_id in requested_extensions:
        payload = extension_results.get(extension_id, {})
        requirement = {
            "extension_id": extension_id,
            "eligible": bool(payload.get("eligible", False)),
            "failed_rules": list(payload.get("failed_rules", ())),
            "reasons": list(payload.get("reasons", ())),
        }
        extension_requirements.append(requirement)
        if requirement["reasons"]:
            hints.extend(f"{extension_id}: {reason}" for reason in requirement["reasons"])
    failure = SolverFailure(
        template_id=DEFAULT_TEMPLATE_ID,
        failed_at_pass="extensions.requested",
        requested_extensions=requested_extensions,
        extension_requirements=tuple(extension_requirements),
        hints=tuple(hints),
    )
    state = attempts[-1].state if attempts else CapabilityState()
    return SolverResult(
        ok=False,
        template_id=DEFAULT_TEMPLATE_ID,
        pass_ids=[],
        passes=(),
        selection_cost=0,
        capabilities=state.capabilities,
        state=state,
        required_outputs=(),
        extension_results=extension_results,
        failure=failure,
    )


def _manifest_outputs(package_dir: Path) -> tuple[str, ...]:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        return ()
    manifest = load_manifest(package_dir)
    outputs = manifest.get("outputs", {})
    if not isinstance(outputs, dict):
        return ()
    return tuple(str(value) for value in outputs.values() if isinstance(value, str))


def _write_solver_failure(package_dir: Path, failure: SolverFailure) -> None:
    failure_path = package_dir / "ir" / "solver_failure.json"
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text(json.dumps(failure.to_json(), indent=2) + "\n")


def solve_existing_package(package_dir: Path | str) -> SolverResult:
    package_path = Path(package_dir)
    manifest = load_manifest(package_path)
    target = _manifest_target(manifest)
    capabilities = set(_backend_declaration(target).target_capabilities)
    analyses: set[str] = set()
    layout_invariants: set[str] = set()
    effect_invariants: set[str] = set()
    for event in _read_pass_trace(package_path):
        capabilities.update(event.get("provides", ()))
        analyses.update(
            str(output["analysis_id"])
            for output in event.get("analysis_produces", ())
            if isinstance(output, dict) and isinstance(output.get("analysis_id"), str)
        )
        layout_invariants.update(
            invariant
            for invariant, satisfied in event.get("requires_satisfied", {})
            .get("layout_invariants", {})
            .items()
            if satisfied
        )
        effect_invariants.update(
            invariant
            for invariant, satisfied in event.get("requires_satisfied", {})
            .get("effect_invariants", {})
            .items()
            if satisfied
        )
    capabilities.add("Package.Emitted@1")
    analyses.add("Analysis.SchedulePlan@1")
    return SolverResult(
        ok=True,
        template_id=RESUME_TEMPLATE_ID,
        pass_ids=[
            str(stage.get("pass"))
            for stage in manifest.get("stages", {}).get("graph", ())
            if isinstance(stage, dict) and stage.get("pass")
        ],
        passes=(),
        selection_cost=0,
        capabilities=tuple(sorted(capabilities)),
        state=CapabilityState(
            capabilities=tuple(sorted(capabilities)),
            layout_invariants=tuple(sorted(layout_invariants)),
            effect_invariants=tuple(sorted(effect_invariants)),
            analyses=tuple(sorted(analyses)),
            target=target,
        ),
        required_outputs=tuple(
            str(value) for value in manifest.get("outputs", {}).values() if isinstance(value, str)
        ),
        extension_results=dict(manifest.get("extensions", {})),
        selection_trace={
            "base_cost": 0,
            "pass_cost": 0,
            "extension_cost": 0,
            "output_cost": len(
                tuple(str(value) for value in manifest.get("outputs", {}).values() if isinstance(value, str))
            ),
            "resume_bonus": -200,
            "requested_extension_bonus": 0,
            "total": len(
                tuple(str(value) for value in manifest.get("outputs", {}).values() if isinstance(value, str))
            )
            - 200,
        },
    )


def _program_identity(program: dict[str, Any]) -> dict[str, Any]:
    kernel = program.get("kernel")
    workload = program.get("workload")
    extensions = program.get("extensions")
    return {
        "entry": str(program.get("entry", "")),
        "kernel_name": str(kernel.get("name", "")) if isinstance(kernel, dict) else "",
        "workload_entry": str(workload.get("entry", "")) if isinstance(workload, dict) else "",
        "requested_extensions": list(extensions.get("requested", ())) if isinstance(extensions, dict) else [],
    }


def _manifest_target(manifest: dict[str, Any]) -> dict[str, str]:
    target = manifest.get("target", {})
    if not isinstance(target, dict):
        return {"backend": "generic", "option": "default"}
    return {
        "backend": str(target.get("backend", "generic")),
        "option": str(target.get("variant") or target.get("option") or "default"),
    }


def _read_pass_trace(package_dir: Path) -> list[dict[str, Any]]:
    trace_path = package_dir / "ir" / "pass_trace.jsonl"
    if not trace_path.exists():
        return []
    return [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]


__all__ = [
    "CapabilityState",
    "ContractSatisfaction",
    "DEFAULT_TEMPLATE_ID",
    "PipelineTemplate",
    "RESUME_TEMPLATE_ID",
    "SOLVER_FAILURE_SCHEMA_ID",
    "SolverFailure",
    "SolverResult",
    "apply_contract_to_state",
    "describe_state_delta",
    "available_pipeline_templates",
    "build_initial_capability_state",
    "default_pipeline_template",
    "evaluate_contract_satisfaction",
    "solve_existing_package",
    "solve_default_pipeline",
    "solve_pipeline",
    "validate_final_artifacts",
]
