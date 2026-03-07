from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from htp.passes.program_model import build_semantic_model, canonicalize_program

from .arch import arch_for, normalize_variant


@dataclass(frozen=True)
class PTOParamSpec:
    name: str
    kind: str
    dtype: str
    role: str | None
    shape: tuple[str, ...]


@dataclass(frozen=True)
class PTOKernelSpec:
    kernel_id: str
    func_id: int
    symbol_name: str
    source: str
    core_type: str
    params: tuple[PTOParamSpec, ...]
    op: str
    attrs: dict[str, Any]


@dataclass(frozen=True)
class PTOOrchestrationSpec:
    source: str
    function_name: str


@dataclass(frozen=True)
class PTOCodegenPlan:
    backend: str
    variant: str
    hardware_profile: str
    pto_runtime_contract: str
    pto_isa_contract: str
    entrypoint: str
    kernels: tuple[PTOKernelSpec, ...]
    orchestration: PTOOrchestrationSpec
    runtime_config: dict[str, object]


def lower_program(program: Mapping[str, Any], *, variant: str | None = None) -> PTOCodegenPlan:
    entrypoint = program.get("entry")
    if not isinstance(entrypoint, str) or not entrypoint:
        raise ValueError("PTO codegen requires program['entry'] to be a non-empty string")

    arch = arch_for(normalize_variant(variant))
    kernel_ir = _kernel_ir_for_program(program)
    kernel_op = _primary_kernel_op(kernel_ir)
    params = tuple(
        PTOParamSpec(
            name=str(argument["name"]),
            kind=str(argument["kind"]),
            dtype=str(argument["dtype"]),
            role=str(argument.get("role")) if argument.get("role") is not None else None,
            shape=tuple(str(dim) for dim in argument.get("shape", ())),
        )
        for argument in kernel_ir.get("args", ())
    )
    kernel = PTOKernelSpec(
        kernel_id=f"{entrypoint}.kernel0",
        func_id=0,
        symbol_name="kernel_entry",
        source=f"codegen/pto/kernels/{arch.core_type}/{entrypoint}.cpp",
        core_type=arch.core_type,
        params=params,
        op=str(kernel_op["op"]),
        attrs=dict(kernel_op.get("attrs", {})),
    )
    orchestration = PTOOrchestrationSpec(
        source=f"codegen/pto/orchestration/{entrypoint}_orchestration.cpp",
        function_name=f"{entrypoint}_orchestrate",
    )
    return PTOCodegenPlan(
        backend=arch.backend,
        variant=arch.variant,
        hardware_profile=arch.hardware_profile,
        pto_runtime_contract="pto-runtime:dev",
        pto_isa_contract=f"pto-isa:{arch.variant}",
        entrypoint=entrypoint,
        kernels=(kernel,),
        orchestration=orchestration,
        runtime_config={
            "runtime": "host_build_graph",
            "platform": arch.variant,
            "aicpu_thread_num": 1,
            "block_dim": 1,
        },
    )


def _kernel_ir_for_program(program: Mapping[str, Any]) -> Mapping[str, Any]:
    kernel_ir = program.get("kernel_ir")
    if isinstance(kernel_ir, Mapping) and isinstance(kernel_ir.get("ops"), list):
        return kernel_ir
    canonical_ast = canonicalize_program(program)
    lowered_kernel_ir, _workload_ir, _entities, _bindings = build_semantic_model(canonical_ast)
    return lowered_kernel_ir


def _primary_kernel_op(kernel_ir: Mapping[str, Any]) -> Mapping[str, Any]:
    ops = kernel_ir.get("ops")
    if not isinstance(ops, list) or not ops:
        raise ValueError("PTO codegen requires a non-empty kernel_ir.ops list")
    primary = ops[0]
    if not isinstance(primary, Mapping):
        raise ValueError("PTO kernel_ir.ops entries must be mappings")
    if str(primary.get("op")) != "elementwise_binary":
        raise ValueError(f"Unsupported PTO kernel op {primary.get('op')!r}")
    return primary


__all__ = [
    "PTOCodegenPlan",
    "PTOKernelSpec",
    "PTOOrchestrationSpec",
    "PTOParamSpec",
    "lower_program",
]
