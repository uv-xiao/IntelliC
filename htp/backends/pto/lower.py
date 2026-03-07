from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .arch import arch_for, normalize_variant


@dataclass(frozen=True)
class PTOKernelSpec:
    kernel_id: str
    func_id: int
    symbol_name: str
    source: str
    core_type: str


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
    kernel = PTOKernelSpec(
        kernel_id=f"{entrypoint}.kernel0",
        func_id=0,
        symbol_name="kernel_entry",
        source=f"codegen/pto/kernels/{arch.core_type}/{entrypoint}.cpp",
        core_type=arch.core_type,
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


__all__ = [
    "PTOCodegenPlan",
    "PTOKernelSpec",
    "PTOOrchestrationSpec",
    "lower_program",
]
