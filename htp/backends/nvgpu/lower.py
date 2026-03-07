from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .arch import arch_for, normalize_profile


@dataclass(frozen=True)
class NVGPUKernelSpec:
    kernel_id: str
    func_id: str
    source: str
    thread_block: tuple[int, int, int]
    shared_memory_bytes: int
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class NVGPULaunchSpec:
    source: str
    function_name: str


@dataclass(frozen=True)
class NVGPUCodegenPlan:
    backend: str
    variant: str
    profile: str
    hardware_profile: str
    codegen_mode: str
    cuda_runtime_contract: str
    cuda_arches: tuple[str, ...]
    entrypoint: str
    kernels: tuple[NVGPUKernelSpec, ...]
    launch: NVGPULaunchSpec


def lower_program(program: Mapping[str, Any], *, profile: str | None = None) -> NVGPUCodegenPlan:
    entrypoint = program.get("entry")
    if not isinstance(entrypoint, str) or not entrypoint:
        raise ValueError("NV-GPU codegen requires program['entry'] to be a non-empty string")

    arch = arch_for(normalize_profile(profile))
    kernel = NVGPUKernelSpec(
        kernel_id=f"{entrypoint}.kernel0",
        func_id=f"{entrypoint}_kernel0",
        source=f"codegen/nvgpu/kernels/{entrypoint}.cu",
        thread_block=(128, 1, 1),
        shared_memory_bytes=0,
        capabilities=arch.capabilities,
    )
    launch = NVGPULaunchSpec(
        source=f"codegen/nvgpu/host/{entrypoint}_launch.py",
        function_name=f"launch_{entrypoint}",
    )
    return NVGPUCodegenPlan(
        backend=arch.backend,
        variant=arch.variant,
        profile=arch.profile,
        hardware_profile=arch.hardware_profile,
        codegen_mode="cuda_source",
        cuda_runtime_contract="cuda-runtime:stub",
        cuda_arches=arch.cuda_arches,
        entrypoint=entrypoint,
        kernels=(kernel,),
        launch=launch,
    )


__all__ = [
    "NVGPUCodegenPlan",
    "NVGPUKernelSpec",
    "NVGPULaunchSpec",
    "lower_program",
]
