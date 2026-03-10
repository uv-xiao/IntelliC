from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from htp.intrinsics import lower_intrinsic, require_handler
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
    arknife: dict[str, Any] | None = None


def lower_program(program: Mapping[str, Any], *, profile: str | None = None) -> NVGPUCodegenPlan:
    entrypoint = program.get("entry")
    if not isinstance(entrypoint, str) or not entrypoint:
        raise ValueError("NV-GPU codegen requires program['entry'] to be a non-empty string")

    arch = arch_for(normalize_profile(profile))
    kernel_ir = _kernel_ir_for_program(program)
    arknife = _arknife_payload_for_program(program)
    if arknife is not None:
        _validate_arknife_payload(arknife, arch=arch)
        kernel_op = _lower_arknife_kernel(kernel_ir, arknife=arknife, arch=arch)
    else:
        kernel_op = _primary_kernel_op(kernel_ir, arch=arch)
    threading = (
        program.get("layout", {}).get("threading", {}) if isinstance(program.get("layout"), Mapping) else {}
    )
    if str(kernel_op.get("op")) in {"matmul", "arknife_mainloop"}:
        default_thread_block = [32, 16, 1] if arch.profile == "blackwell" else [16, 16, 1]
    else:
        default_thread_block = [128, 1, 1]
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
        arknife=arknife,
    )


def _kernel_ir_for_program(program: Mapping[str, Any]) -> Mapping[str, Any]:
    kernel_ir = program.get("kernel_ir")
    if isinstance(kernel_ir, Mapping) and isinstance(kernel_ir.get("ops"), list):
        return kernel_ir
    canonical_ast = canonicalize_program(program)
    lowered_kernel_ir, _workload_ir, _entities, _bindings = build_semantic_model(canonical_ast)
    return lowered_kernel_ir


def _primary_kernel_op(kernel_ir: Mapping[str, Any], *, arch: Any) -> Mapping[str, Any]:
    ops = kernel_ir.get("ops")
    if not isinstance(ops, list) or not ops:
        raise ValueError("NV-GPU codegen requires a non-empty kernel_ir.ops list")
    if _is_fused_elementwise_kernel(ops):
        return _lower_fused_elementwise_kernel(ops, arch=arch)
    if len(ops) > 1:
        return _lower_composite_kernel(ops, kernel_ir=kernel_ir, arch=arch)
    primary = ops[0]
    if not isinstance(primary, Mapping):
        raise ValueError("NV-GPU kernel_ir.ops entries must be mappings")
    intrinsic = str(primary.get("intrinsic", ""))
    require_handler("nvgpu", intrinsic, role="lower")
    return _attach_profile_plan(dict(lower_intrinsic("nvgpu", primary)), arch=arch)


def _arknife_payload_for_program(program: Mapping[str, Any]) -> dict[str, Any] | None:
    canonical = program.get("canonical_ast")
    if isinstance(canonical, Mapping) and isinstance(canonical.get("ark"), Mapping):
        return dict(canonical["ark"])
    arknife = program.get("ark")
    if isinstance(arknife, Mapping):
        return dict(arknife)
    return None


def _launch_geometry_for_op(op: Mapping[str, Any]) -> NVGPULaunchGeometry:
    if str(op.get("op")) in {"matmul", "arknife_mainloop"}:
        attrs = op.get("attrs", {})
        return NVGPULaunchGeometry(kind="grid_2d", extents=(str(attrs["m"]), str(attrs["n"])))
    if str(op.get("op")) == "composite":
        attrs = op.get("attrs", {})
        shape = [str(value) for value in attrs.get("shape", ["size"])]
        if len(shape) >= 2:
            return NVGPULaunchGeometry(kind="grid_2d", extents=(shape[0], shape[1]))
        extent = shape[0] if shape else "size"
        return NVGPULaunchGeometry(kind="grid_1d", extents=(extent,))
    attrs = op.get("attrs", {})
    shape = attrs.get("shape", ["size"])
    extent = str(shape[0]) if shape else "size"
    return NVGPULaunchGeometry(kind="grid_1d", extents=(extent,))


def _is_fused_elementwise_kernel(ops: list[Any]) -> bool:
    return len(ops) > 1 and all(
        isinstance(op, Mapping) and str(op.get("op")) in {"elementwise_binary", "elementwise_unary"}
        for op in ops
    )


def _lower_fused_elementwise_kernel(ops: list[Any], *, arch: Any) -> dict[str, Any]:
    lowered_ops: list[dict[str, Any]] = []
    shape: list[str] | None = None
    dtype: str | None = None
    for op in ops:
        intrinsic = str(op.get("intrinsic", ""))
        require_handler("nvgpu", intrinsic, role="lower")
        lowered = lower_intrinsic("nvgpu", op)
        lowered_ops.append(dict(lowered))
        attrs = lowered.get("attrs", {})
        if shape is None and isinstance(attrs, Mapping) and isinstance(attrs.get("shape"), list):
            shape = [str(value) for value in attrs["shape"]]
        if dtype is None and isinstance(attrs, Mapping) and isinstance(attrs.get("dtype"), str):
            dtype = str(attrs["dtype"])
    return _attach_profile_plan(
        {
            "op": "fused_elementwise",
            "attrs": {
                "ops": lowered_ops,
                "shape": shape or ["size"],
                "dtype": dtype or "f32",
            },
        },
        arch=arch,
    )


def _lower_composite_kernel(ops: list[Any], *, kernel_ir: Mapping[str, Any], arch: Any) -> dict[str, Any]:
    lowered_ops: list[dict[str, Any]] = []
    for op in ops:
        if not isinstance(op, Mapping):
            raise ValueError("NV-GPU composite kernels require mapping ops.")
        intrinsic = str(op.get("intrinsic", ""))
        require_handler("nvgpu", intrinsic, role="lower")
        lowered_ops.append(dict(lower_intrinsic("nvgpu", op)))
    output_shape = _first_output_shape(kernel_ir)
    return _attach_profile_plan(
        {
            "op": "composite",
            "attrs": {
                "ops": lowered_ops,
                "shape": output_shape or ["size"],
            },
        },
        arch=arch,
    )


def _first_output_shape(kernel_ir: Mapping[str, Any]) -> list[str] | None:
    args = kernel_ir.get("args", ())
    if not isinstance(args, list):
        return None
    for argument in args:
        if not isinstance(argument, Mapping):
            continue
        if str(argument.get("role")) in {"output", "inout"}:
            return [str(value) for value in argument.get("shape", ())]
    return None


def _validate_arknife_payload(arknife: Mapping[str, Any], *, arch: Any) -> None:
    hardware = arknife.get("hardware")
    if not isinstance(hardware, Mapping):
        raise ValueError("Arknife programs require ark.hardware metadata.")
    if hardware.get("profile") != arch.profile:
        raise ValueError(
            f"Arknife hardware profile {hardware.get('profile')!r} does not match NV-GPU target profile {arch.profile!r}."
        )
    if hardware.get("backend") != arch.backend:
        raise ValueError(
            f"Arknife hardware backend {hardware.get('backend')!r} does not match NV-GPU backend {arch.backend!r}."
        )
    available = set(arch.capabilities)
    for op in arknife.get("instructions", ()):
        if not isinstance(op, Mapping):
            continue
        capability = op.get("capability")
        if capability is None:
            continue
        if capability not in available:
            raise ValueError(
                f"NV-GPU profile {arch.profile!r} does not support Arknife instruction "
                f"{op.get('instruction')!r} requiring capability {capability!r}."
            )


def _lower_arknife_kernel(
    kernel_ir: Mapping[str, Any], *, arknife: Mapping[str, Any], arch: Any
) -> Mapping[str, Any]:
    ops = list(kernel_ir.get("ops", ()))
    if not ops:
        raise ValueError("Arknife NV-GPU lowering requires a non-empty kernel_ir.ops list.")
    public_buffers = {
        str(argument["name"]): argument
        for argument in kernel_ir.get("args", ())
        if argument.get("kind") == "buffer"
    }
    output_buffer = next((arg for arg in public_buffers.values() if arg.get("role") == "output"), None)
    if output_buffer is None:
        raise ValueError("Arknife NV-GPU lowering requires an output buffer argument.")
    output_shape = [str(dim) for dim in output_buffer.get("shape", ())] or ["M", "N"]
    instruction_plan = [
        {
            "instruction": str(op.get("op")),
            **({"capability": str(op["capability"])} if op.get("capability") is not None else {}),
            "attrs": dict(op.get("attrs", {})),
        }
        for op in ops
    ]
    return _attach_profile_plan(
        {
            "op": "arknife_mainloop",
            "attrs": {
                "dtype": str(output_buffer.get("dtype", "f32")),
                "m": output_shape[0] if output_shape else "M",
                "n": output_shape[1] if len(output_shape) > 1 else "N",
                "k": "K",
                "instruction_plan": instruction_plan,
                "hardware": dict(arknife.get("hardware", {})),
                "channels": [dict(item) for item in arknife.get("channels", ())],
            },
        },
        arch=arch,
    )


def _attach_profile_plan(lowered: dict[str, Any], *, arch: Any) -> dict[str, Any]:
    attrs = dict(lowered.get("attrs", {}))
    profile_plan = dict(attrs.get("profile_plan", {}))
    if not profile_plan:
        profile_plan = _profile_plan_for_arch(arch, op=str(lowered.get("op", "")))
    if profile_plan:
        attrs["profile_plan"] = profile_plan
    lowered["attrs"] = attrs
    return lowered


def _profile_plan_for_arch(arch: Any, *, op: str) -> dict[str, Any]:
    if op not in {"matmul", "arknife_mainloop", "composite", "fused_elementwise"}:
        return {}
    if arch.profile == "blackwell":
        return {
            "profile": arch.profile,
            "matrix_engine": "wgmma" if op in {"matmul", "arknife_mainloop"} else "simt",
            "async_loader": "tma" if op in {"matmul", "arknife_mainloop"} else "cp.async.bulk",
            "pipeline_stages": 3,
            "cluster_shape": [2, 1, 1],
        }
    return {
        "profile": arch.profile,
        "matrix_engine": "mma_sync" if op in {"matmul", "arknife_mainloop"} else "simt",
        "async_loader": "cp_async",
        "pipeline_stages": 2,
        "cluster_shape": [1, 1, 1],
    }


__all__ = [
    "NVGPUCodegenPlan",
    "NVGPUKernelSpec",
    "NVGPULaunchGeometry",
    "NVGPULaunchSpec",
    "NVGPUParamSpec",
    "lower_program",
]
