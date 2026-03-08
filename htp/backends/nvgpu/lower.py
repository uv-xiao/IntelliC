from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from htp.intrinsics import require_handler
from htp.passes.program_model import build_semantic_model, canonicalize_program

from .arch import arch_for, normalize_profile


@dataclass(frozen=True)
class NVGPUParamSpec:
    name: str
    kind: str
    dtype: str
    role: str | None
    shape: tuple[str, ...]


@dataclass(frozen=True)
class NVGPULaunchGeometry:
    kind: str
    extents: tuple[str, ...]


@dataclass(frozen=True)
class NVGPUKernelSpec:
    kernel_id: str
    func_id: str
    source: str
    thread_block: tuple[int, int, int]
    shared_memory_bytes: int
    capabilities: tuple[str, ...]
    params: tuple[NVGPUParamSpec, ...]
    launch: NVGPULaunchGeometry
    op: str
    attrs: dict[str, Any]


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
    kernel_ir = _kernel_ir_for_program(program)
    kernel_op = _primary_kernel_op(kernel_ir)
    threading = (
        program.get("layout", {}).get("threading", {}) if isinstance(program.get("layout"), Mapping) else {}
    )
    default_thread_block = [16, 16, 1] if str(kernel_op.get("op")) == "matmul" else [128, 1, 1]
    thread_block = tuple(int(value) for value in threading.get("thread_block", default_thread_block))
    params = tuple(
        NVGPUParamSpec(
            name=str(argument["name"]),
            kind=str(argument["kind"]),
            dtype=str(argument["dtype"]),
            role=str(argument.get("role")) if argument.get("role") is not None else None,
            shape=tuple(str(dim) for dim in argument.get("shape", ())),
        )
        for argument in kernel_ir.get("args", ())
    )
    kernel = NVGPUKernelSpec(
        kernel_id=f"{entrypoint}.kernel0",
        func_id=f"{entrypoint}_kernel0",
        source=f"codegen/nvgpu/kernels/{entrypoint}.cu",
        thread_block=thread_block,
        shared_memory_bytes=0,
        capabilities=arch.capabilities,
        params=params,
        launch=_launch_geometry_for_op(kernel_op),
        op=str(kernel_op["op"]),
        attrs=dict(kernel_op.get("attrs", {})),
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
        cuda_runtime_contract="cuda-runtime:driver",
        cuda_arches=arch.cuda_arches,
        entrypoint=entrypoint,
        kernels=(kernel,),
        launch=launch,
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
        raise ValueError("NV-GPU codegen requires a non-empty kernel_ir.ops list")
    primary = ops[0]
    if not isinstance(primary, Mapping):
        raise ValueError("NV-GPU kernel_ir.ops entries must be mappings")
    intrinsic = str(primary.get("intrinsic", ""))
    require_handler("nvgpu", intrinsic, role="lower")
    return primary


def _launch_geometry_for_op(op: Mapping[str, Any]) -> NVGPULaunchGeometry:
    if str(op.get("op")) == "matmul":
        attrs = op.get("attrs", {})
        return NVGPULaunchGeometry(kind="grid_2d", extents=(str(attrs["m"]), str(attrs["n"])))
    attrs = op.get("attrs", {})
    shape = attrs.get("shape", ["size"])
    extent = str(shape[0]) if shape else "size"
    return NVGPULaunchGeometry(kind="grid_1d", extents=(extent,))


__all__ = [
    "NVGPUCodegenPlan",
    "NVGPUKernelSpec",
    "NVGPULaunchGeometry",
    "NVGPULaunchSpec",
    "NVGPUParamSpec",
    "lower_program",
]
