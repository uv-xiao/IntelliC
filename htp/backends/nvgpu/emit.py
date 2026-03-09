from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from htp.schemas import MANIFEST_SCHEMA_ID

from .declarations import NVGPU_PROJECT_DIR, NVGPU_TOOLCHAIN_PATH, declaration_for
from .lower import NVGPUCodegenPlan, NVGPUKernelSpec, lower_program

NVGPU_CODEGEN_SCHEMA_ID = "htp.nvgpu.codegen.v1"
NVGPU_TOOLCHAIN_SCHEMA_ID = "htp.nvgpu.toolchain.v1"


def emit_package(
    package_dir: Path | str,
    *,
    program: Mapping[str, Any],
    profile: str | None = None,
) -> dict[str, Any]:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)

    plan = lower_program(program, profile=profile)
    _write_codegen_tree(package_path, plan)

    manifest = _load_manifest(package_path)
    manifest["schema"] = MANIFEST_SCHEMA_ID
    manifest.setdefault("stages", {"current": "s00", "graph": []})
    target = dict(manifest.get("target", {})) if isinstance(manifest.get("target"), Mapping) else {}
    target.update(
        {
            "backend": plan.backend,
            "variant": plan.variant,
            "hardware_profile": plan.hardware_profile,
        }
    )
    manifest["target"] = target

    outputs = dict(manifest.get("outputs", {}))
    outputs.update(declaration_for(profile).artifact_contract.as_manifest_outputs())
    manifest["outputs"] = outputs

    extensions = dict(manifest.get("extensions", {}))
    nvgpu_extension = dict(extensions.get("nvgpu", {}))
    nvgpu_extension.update(
        {
            "kernel_project_dir": NVGPU_PROJECT_DIR.as_posix(),
            "launch_entry": {
                "source": _project_relative(plan.launch.source),
                "function_name": plan.launch.function_name,
            },
            "cuda_runtime_contract": plan.cuda_runtime_contract,
            "codegen_mode": plan.codegen_mode,
            "toolchain_manifest": NVGPU_TOOLCHAIN_PATH.as_posix(),
        }
    )
    extensions["nvgpu"] = nvgpu_extension
    manifest["extensions"] = extensions

    manifest_path = package_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _write_codegen_tree(package_dir: Path, plan: NVGPUCodegenPlan) -> None:
    project_dir = package_dir / NVGPU_PROJECT_DIR
    codegen_index_path = project_dir / "nvgpu_codegen.json"
    toolchain_path = package_dir / NVGPU_TOOLCHAIN_PATH

    launch_path = package_dir / plan.launch.source
    launch_path.parent.mkdir(parents=True, exist_ok=True)
    launch_path.write_text(_launch_source(plan))

    for kernel in plan.kernels:
        kernel_path = package_dir / kernel.source
        kernel_path.parent.mkdir(parents=True, exist_ok=True)
        kernel_path.write_text(_kernel_source(kernel))

    codegen_index_path.parent.mkdir(parents=True, exist_ok=True)
    codegen_index_path.write_text(json.dumps(_codegen_index(plan), indent=2) + "\n")
    toolchain_path.parent.mkdir(parents=True, exist_ok=True)
    toolchain_path.write_text(json.dumps(_toolchain_payload(plan), indent=2) + "\n")


def _codegen_index(plan: NVGPUCodegenPlan) -> dict[str, Any]:
    return {
        "schema": NVGPU_CODEGEN_SCHEMA_ID,
        "backend": plan.backend,
        "variant": plan.variant,
        "hardware_profile": plan.hardware_profile,
        **({"arknife": dict(plan.arknife)} if plan.arknife is not None else {}),
        "entrypoint": plan.entrypoint,
        "launch": {
            "source": plan.launch.source,
            "function_name": plan.launch.function_name,
        },
        "kernels": [
            {
                "kernel_id": kernel.kernel_id,
                "func_id": kernel.func_id,
                "source": kernel.source,
                "thread_block": list(kernel.thread_block),
                "shared_memory_bytes": kernel.shared_memory_bytes,
                "capabilities": list(kernel.capabilities),
                "params": [
                    {
                        "name": param.name,
                        "kind": param.kind,
                        "dtype": param.dtype,
                        "role": param.role,
                        "shape": list(param.shape),
                    }
                    for param in kernel.params
                ],
                "launch": {
                    "kind": kernel.launch.kind,
                    "extents": list(kernel.launch.extents),
                },
                "op": kernel.op,
                "attrs": dict(kernel.attrs),
                **(
                    {"instruction_plan": [dict(item) for item in kernel.attrs.get("instruction_plan", ())]}
                    if isinstance(kernel.attrs.get("instruction_plan"), list)
                    else {}
                ),
            }
            for kernel in plan.kernels
        ],
    }


def _toolchain_payload(plan: NVGPUCodegenPlan) -> dict[str, Any]:
    derived_outputs = [
        f"build/nvgpu/{plan.entrypoint}.ptx",
        f"build/nvgpu/{plan.entrypoint}.cubin",
    ]
    return {
        "schema": NVGPU_TOOLCHAIN_SCHEMA_ID,
        "backend": plan.backend,
        "variant": plan.variant,
        "hardware_profile": plan.hardware_profile,
        "codegen_mode": plan.codegen_mode,
        "cuda_runtime_contract": plan.cuda_runtime_contract,
        "cuda_arches": list(plan.cuda_arches),
        "derived_outputs": derived_outputs,
    }


def _launch_source(plan: NVGPUCodegenPlan) -> str:
    kernel = plan.kernels[0]
    argument_names = ", ".join(param.name for param in kernel.params)
    return "\n".join(
        (
            "from htp.runtime import call_kernel, default_runtime",
            "",
            f'def {plan.launch.function_name}({argument_names}, mode="sim", trace=None, runtime=None):',
            "    resolved_runtime = default_runtime() if runtime is None else runtime",
            "    return call_kernel(",
            f'        "{kernel.kernel_id}",',
            f"        args=({argument_names},),",
            "        mode=mode,",
            "        trace=trace,",
            "        runtime=resolved_runtime,",
            "        artifacts={",
            f'            "backend": "{plan.backend}",',
            f'            "variant": "{plan.variant}",',
            f'            "hardware_profile": "{plan.hardware_profile}",',
            f'            "kernel_source": "{kernel.source}",',
            f'            "kernel_params": {json.dumps([param.name for param in kernel.params])},',
            "        },",
            "    )",
            "",
        )
    )


def _kernel_source(kernel: NVGPUKernelSpec) -> str:
    if kernel.op == "arknife_mainloop":
        return _arknife_kernel_source(kernel)
    if kernel.op == "matmul":
        return _matmul_kernel_source(kernel)
    if kernel.op == "composite":
        return _composite_kernel_source(kernel)
    return _fused_elementwise_source(kernel)


def _matmul_kernel_source(kernel: NVGPUKernelSpec) -> str:
    return "\n".join(
        (
            "#include <cuda_runtime.h>",
            "",
            f'extern "C" __global__ void {kernel.func_id}(const float* A, const float* B, float* C, int M, int N, int K) {{',
            "  const int row = blockIdx.y * blockDim.y + threadIdx.y;",
            "  const int col = blockIdx.x * blockDim.x + threadIdx.x;",
            "  if (row >= M || col >= N) {",
            "    return;",
            "  }",
            "  float accum = 0.0f;",
            "  for (int k = 0; k < K; ++k) {",
            "    accum += A[row * K + k] * B[k * N + col];",
            "  }",
            "  C[row * N + col] = accum;",
            "}",
            "",
        )
    )


def _arknife_kernel_source(kernel: NVGPUKernelSpec) -> str:
    attrs = kernel.attrs
    instruction_plan = [dict(item) for item in attrs.get("instruction_plan", ())]
    hardware = dict(attrs.get("hardware", {}))
    channels = [dict(item) for item in attrs.get("channels", ())]
    comment_lines = [
        f"// Arknife hardware profile: {hardware.get('hardware_profile', '')}",
        f"// Capabilities: {', '.join(str(item) for item in hardware.get('capabilities', ()))}",
    ]
    for channel in channels:
        comment_lines.append(
            f"// Channel {channel.get('name')}: scope={channel.get('scope')} memory={channel.get('memory')} kind={channel.get('kind')}"
        )
    for item in instruction_plan:
        comment_lines.append(f"// instruction: {item.get('instruction')}")
    return "\n".join(
        (
            "#include <cuda_runtime.h>",
            "#include <math.h>",
            "",
            *comment_lines,
            "",
            f'extern "C" __global__ void {kernel.func_id}({_param_signature(kernel)}) {{',
            "  const int row = blockIdx.y * blockDim.y + threadIdx.y;",
            "  const int col = blockIdx.x * blockDim.x + threadIdx.x;",
            "  if (row >= M || col >= N) {",
            "    return;",
            "  }",
            "  // HTP keeps the Arknife-style instruction plan as emitted metadata and",
            "  // annotated source. The numerical fallback below preserves semantics on",
            "  // available hardware even when the exact low-level instruction sequence is",
            "  // profile-specific.",
            "  float accum = 0.0f;",
            "  for (int k = 0; k < K; ++k) {",
            "    accum += static_cast<float>(A[row * K + k]) * static_cast<float>(B[k * N + col]);",
            "  }",
            "  C[row * N + col] = accum;",
            "}",
            "",
        )
    )


def _fused_elementwise_source(kernel: NVGPUKernelSpec) -> str:
    attrs = kernel.attrs
    lowered_ops = attrs.get("ops", [])
    if not isinstance(lowered_ops, list) or not lowered_ops:
        operator = str(attrs.get("operator", "add"))
        lowered_ops = [
            {
                "op": "elementwise_binary",
                "attrs": {
                    "operator": operator,
                },
                "effects": {},
                "inputs": ["lhs", "rhs"],
                "outputs": ["out"],
            }
        ]

    statements = [
        "#include <cuda_runtime.h>",
        "#include <math.h>",
        "",
        f'extern "C" __global__ void {kernel.func_id}({_param_signature(kernel)}) {{',
        "  const int idx = blockIdx.x * blockDim.x + threadIdx.x;",
        "  if (idx >= size) {",
        "    return;",
        "  }",
    ]
    env = {param.name: f"{param.name}[idx]" for param in kernel.params if param.kind == "buffer"}
    for op in lowered_ops:
        if not isinstance(op, Mapping):
            continue
        inputs = [str(name) for name in op.get("inputs", ())]
        outputs = [str(name) for name in op.get("outputs", ())]
        attrs = op.get("attrs", {})
        if not outputs:
            continue
        out_name = outputs[0]
        expr = _cuda_expression(op_name=str(op.get("op")), inputs=inputs, attrs=attrs, env=env)
        local_name = f"{out_name}_value"
        statements.append(f"  float {local_name} = {expr};")
        env[out_name] = local_name
    for param in kernel.params:
        if param.kind == "buffer" and param.role in {"output", "inout"} and param.name in env:
            statements.append(f"  {param.name}[idx] = {env[param.name]};")
    statements.extend(["}", ""])
    return "\n".join(statements)


def _composite_kernel_source(kernel: NVGPUKernelSpec) -> str:
    attrs = kernel.attrs
    lowered_ops = attrs.get("ops", [])
    comment_lines = ["// HTP composite kernel fallback", *[f"// op: {dict(op)}" for op in lowered_ops]]
    size_expr = _linear_extent_expr(kernel)
    input_buffers = [param for param in kernel.params if param.kind == "buffer" and param.role == "input"]
    output_buffers = [
        param for param in kernel.params if param.kind == "buffer" and param.role in {"output", "inout"}
    ]
    write_expr = f"{input_buffers[0].name}[idx]" if input_buffers else "0.0f"
    statements = [
        "#include <cuda_runtime.h>",
        "#include <math.h>",
        "",
        *comment_lines,
        "",
        f'extern "C" __global__ void {kernel.func_id}({_param_signature(kernel)}) {{',
        "  const int idx = blockIdx.x * blockDim.x + threadIdx.x;",
        f"  if (idx >= {size_expr}) {{",
        "    return;",
        "  }",
    ]
    for param in output_buffers:
        statements.append(f"  {param.name}[idx] = {write_expr};")
    statements.extend(["}", ""])
    return "\n".join(statements)


def _linear_extent_expr(kernel: NVGPUKernelSpec) -> str:
    for param in kernel.params:
        if param.kind != "buffer" or param.role not in {"output", "inout"}:
            continue
        if not param.shape:
            break
        dims = [str(dim) for dim in param.shape if str(dim)]
        if dims:
            return " * ".join(dims)
    return "size"


def _param_signature(kernel: NVGPUKernelSpec) -> str:
    parts: list[str] = []
    for param in kernel.params:
        if param.kind == "buffer":
            qualifier = "const float*" if param.role == "input" else "float*"
            parts.append(f"{qualifier} {param.name}")
        else:
            parts.append(f"int {param.name}")
    return ", ".join(parts)


def _cuda_expression(
    *, op_name: str, inputs: list[str], attrs: Mapping[str, Any], env: Mapping[str, str]
) -> str:
    if op_name == "elementwise_binary":
        lhs = _resolve_scalar_expression(inputs=inputs, index=0, const_key="lhs_const", attrs=attrs, env=env)
        rhs = _resolve_scalar_expression(inputs=inputs, index=1, const_key="rhs_const", attrs=attrs, env=env)
        operator = str(attrs.get("operator", "add"))
        if operator == "add":
            return f"({lhs} + {rhs})"
        if operator == "sub":
            return f"({lhs} - {rhs})"
        if operator == "mul":
            return f"({lhs} * {rhs})"
        if operator == "div":
            return f"({lhs} / {rhs})"
        raise ValueError(f"Unsupported NV-GPU elementwise_binary operator {operator!r}.")
    if op_name == "elementwise_unary":
        source = env[inputs[0]]
        operator = str(attrs.get("operator", "identity"))
        if operator == "identity":
            return source
        if operator == "neg":
            return f"(-{source})"
        if operator == "recip":
            return f"(1.0f / {source})"
        if operator == "exp":
            return f"expf({source})"
        if operator == "sigmoid":
            return f"(1.0f / (1.0f + expf(-{source})))"
        raise ValueError(f"Unsupported NV-GPU elementwise_unary operator {operator!r}.")
    raise ValueError(f"Unsupported NV-GPU fused op {op_name!r}.")


def _resolve_scalar_expression(
    *,
    inputs: list[str],
    index: int,
    const_key: str,
    attrs: Mapping[str, Any],
    env: Mapping[str, str],
) -> str:
    if len(inputs) > index:
        return env[inputs[index]]
    if const_key in attrs:
        return _float_literal(attrs[const_key])
    raise ValueError(f"Missing NV-GPU fused operand {index} for attrs={attrs!r}.")


def _float_literal(value: Any) -> str:
    literal = f"{float(value):.8g}"
    if "." not in literal and "e" not in literal and "E" not in literal:
        literal = f"{literal}.0"
    return f"{literal}f"


def _project_relative(source_path: str) -> str:
    source = PurePosixPath(source_path)
    return source.relative_to(NVGPU_PROJECT_DIR).as_posix()


def _load_manifest(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text())


__all__ = [
    "NVGPU_CODEGEN_SCHEMA_ID",
    "NVGPU_PROJECT_DIR",
    "NVGPU_TOOLCHAIN_PATH",
    "NVGPU_TOOLCHAIN_SCHEMA_ID",
    "emit_package",
]
