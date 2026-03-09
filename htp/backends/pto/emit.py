from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from htp.schemas import MANIFEST_SCHEMA_ID

from .declarations import PTO_PROJECT_DIR, PTO_TOOLCHAIN_PATH, declaration_for
from .lower import PTOCodegenPlan, PTOKernelSpec, lower_program

PTO_CODEGEN_SCHEMA_ID = "htp.pto.codegen.v1"
PTO_TOOLCHAIN_SCHEMA_ID = "htp.pto.toolchain.v1"


def emit_package(
    package_dir: Path | str,
    *,
    program: Mapping[str, Any],
    variant: str | None = None,
) -> dict[str, Any]:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)

    plan = lower_program(program, variant=variant)
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
    outputs.update(declaration_for(plan.variant).artifact_contract.as_manifest_outputs())
    manifest["outputs"] = outputs

    extensions = dict(manifest.get("extensions", {}))
    pto_extension = dict(extensions.get("pto", {}))
    pto_extension.update(
        {
            "platform": plan.variant,
            "kernel_project_dir": PTO_PROJECT_DIR.as_posix(),
            "orchestration_entry": {
                "source": _project_relative(plan.orchestration.source),
                "function_name": plan.orchestration.function_name,
            },
            "runtime_config": {
                "runtime": plan.runtime_config["runtime"],
                "aicpu_thread_num": plan.runtime_config["aicpu_thread_num"],
                "block_dim": plan.runtime_config["block_dim"],
            },
            "pto_runtime_contract": plan.pto_runtime_contract,
            "pto_isa_contract": plan.pto_isa_contract,
            "toolchain_manifest": PTO_TOOLCHAIN_PATH.as_posix(),
        }
    )
    extensions["pto"] = pto_extension
    manifest["extensions"] = extensions

    manifest_path = package_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _write_codegen_tree(package_dir: Path, plan: PTOCodegenPlan) -> None:
    project_dir = package_dir / PTO_PROJECT_DIR
    kernel_config_path = project_dir / "kernel_config.py"
    codegen_index_path = project_dir / "pto_codegen.json"
    toolchain_path = package_dir / PTO_TOOLCHAIN_PATH

    orchestration_path = package_dir / plan.orchestration.source
    orchestration_path.parent.mkdir(parents=True, exist_ok=True)
    orchestration_path.write_text(_orchestration_source(plan))

    for kernel in plan.kernels:
        kernel_path = package_dir / kernel.source
        kernel_path.parent.mkdir(parents=True, exist_ok=True)
        kernel_path.write_text(_kernel_source(kernel, variant=plan.variant))

    kernel_config_path.parent.mkdir(parents=True, exist_ok=True)
    kernel_config_path.write_text(_kernel_config_text(plan))
    codegen_index_path.write_text(json.dumps(_codegen_index(plan), indent=2) + "\n")
    toolchain_path.parent.mkdir(parents=True, exist_ok=True)
    toolchain_path.write_text(json.dumps(_toolchain_payload(plan), indent=2) + "\n")


def _codegen_index(plan: PTOCodegenPlan) -> dict[str, Any]:
    return {
        "schema": PTO_CODEGEN_SCHEMA_ID,
        "backend": plan.backend,
        "variant": plan.variant,
        "entrypoint": plan.entrypoint,
        "orchestration": {
            "source": plan.orchestration.source,
            "function_name": plan.orchestration.function_name,
        },
        "kernels": [
            {
                "kernel_id": kernel.kernel_id,
                "func_id": kernel.func_id,
                "symbol_name": kernel.symbol_name,
                "source": kernel.source,
                "core_type": kernel.core_type,
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
                "op": kernel.op,
                "attrs": dict(kernel.attrs),
            }
            for kernel in plan.kernels
        ],
    }


def _kernel_config_text(plan: PTOCodegenPlan) -> str:
    payload = {
        "KERNELS": [
            {
                "func_id": kernel.func_id,
                "source": _project_relative(kernel.source),
                "core_type": kernel.core_type,
            }
            for kernel in plan.kernels
        ],
        "ORCHESTRATION": {
            "source": _project_relative(plan.orchestration.source),
            "function_name": plan.orchestration.function_name,
        },
        "RUNTIME_CONFIG": dict(plan.runtime_config),
    }
    return "\n".join(
        (
            f"KERNELS = {payload['KERNELS']!r}",
            f"ORCHESTRATION = {payload['ORCHESTRATION']!r}",
            f"RUNTIME_CONFIG = {payload['RUNTIME_CONFIG']!r}",
            "",
        )
    )


def _toolchain_payload(plan: PTOCodegenPlan) -> dict[str, Any]:
    return {
        "schema": PTO_TOOLCHAIN_SCHEMA_ID,
        "backend": plan.backend,
        "variant": plan.variant,
        "platform": plan.variant,
        "runtime_name": plan.runtime_config["runtime"],
        "pto_runtime_contract": plan.pto_runtime_contract,
        "pto_isa_contract": plan.pto_isa_contract,
        "compiler_contract": None if plan.variant == "a2a3sim" else "cann:stub",
        "env": {"PTO_ISA_ROOT": "auto"},
        "compile_flags": [],
        "derived_outputs": [
            "build/pto/runtime/libhost_runtime.so",
            "build/pto/runtime/libaicpu_runtime.so",
            "build/pto/runtime/aicore_runtime.bin",
            f"build/pto/orchestration/{plan.entrypoint}_orchestration.so",
            *[f"build/pto/kernels/{kernel.func_id}.bin" for kernel in plan.kernels],
        ],
    }


def _orchestration_source(plan: PTOCodegenPlan) -> str:
    return "\n".join(
        (
            '#include "runtime.h"',
            "#include <cstdint>",
            "#include <iostream>",
            "",
            f'extern "C" int {plan.orchestration.function_name}(Runtime* runtime, uint64_t* args, int arg_count) {{',
            "    if (runtime == nullptr) {",
            "        std::cerr << \"orchestration received null runtime\" << '\\n';",
            "        return -1;",
            "    }",
            "    if (arg_count < 7) {",
            "        std::cerr << \"expected args [lhs, rhs, out, size_lhs, size_rhs, size_out, size]\" << '\\n';",
            "        return -1;",
            "    }",
            "    void* host_lhs = reinterpret_cast<void*>(args[0]);",
            "    void* host_rhs = reinterpret_cast<void*>(args[1]);",
            "    void* host_out = reinterpret_cast<void*>(args[2]);",
            "    size_t size_lhs = static_cast<size_t>(args[3]);",
            "    size_t size_rhs = static_cast<size_t>(args[4]);",
            "    size_t size_out = static_cast<size_t>(args[5]);",
            "    int size = static_cast<int>(args[6]);",
            "",
            "    void* dev_lhs = runtime->host_api.device_malloc(size_lhs);",
            "    void* dev_rhs = runtime->host_api.device_malloc(size_rhs);",
            "    void* dev_out = runtime->host_api.device_malloc(size_out);",
            "    if (!dev_lhs || !dev_rhs || !dev_out) {",
            "        std::cerr << \"failed to allocate device buffers\" << '\\n';",
            "        return -1;",
            "    }",
            "    runtime->host_api.copy_to_device(dev_lhs, host_lhs, size_lhs);",
            "    runtime->host_api.copy_to_device(dev_rhs, host_rhs, size_rhs);",
            "    runtime->record_tensor_pair(host_out, dev_out, size_out);",
            "",
            "    uint64_t kernel_args[4];",
            "    kernel_args[0] = reinterpret_cast<uint64_t>(dev_lhs);",
            "    kernel_args[1] = reinterpret_cast<uint64_t>(dev_rhs);",
            "    kernel_args[2] = reinterpret_cast<uint64_t>(dev_out);",
            "    kernel_args[3] = static_cast<uint64_t>(size);",
            f"    int task0 = runtime->add_task(kernel_args, 4, {plan.kernels[0].func_id}, {_core_type_expr(plan.kernels[0].core_type)});",
            "    if (task0 < 0) {",
            "        std::cerr << \"failed to add PTO vector task\" << '\\n';",
            "        return -1;",
            "    }",
            "    return 0;",
            "}",
            "",
        )
    )


def _kernel_source(kernel: PTOKernelSpec, *, variant: str) -> str:
    if variant == "a2a3sim":
        return _sim_kernel_source(kernel)
    return _device_kernel_source(kernel)


def _sim_kernel_source(kernel: PTOKernelSpec) -> str:
    operator = str(kernel.attrs.get("operator", "add"))
    operator_expr = "+" if operator == "add" else "*"
    return "\n".join(
        (
            "#include <cstdint>",
            "",
            "#ifndef __aicore__",
            "#define __aicore__",
            "#endif",
            "",
            f'extern "C" __aicore__ void {kernel.symbol_name}(int64_t* args) {{',
            "    float* lhs = reinterpret_cast<float*>(args[0]);",
            "    float* rhs = reinterpret_cast<float*>(args[1]);",
            "    float* out = reinterpret_cast<float*>(args[2]);",
            "    int size = static_cast<int>(args[3]);",
            "    for (int index = 0; index < size; ++index) {",
            f"        out[index] = lhs[index] {operator_expr} rhs[index];",
            "    }",
            "}",
            "",
        )
    )


def _device_kernel_source(kernel: PTOKernelSpec) -> str:
    operator = str(kernel.attrs.get("operator", "add"))
    math_intrinsic = "TADD" if operator == "add" else "TMUL"
    return "\n".join(
        (
            "#include <cstdint>",
            "#include <pto/pto-inst.hpp>",
            "",
            "using namespace pto;",
            "",
            "#ifndef __gm__",
            "#define __gm__",
            "#endif",
            "",
            "#ifndef __aicore__",
            "#define __aicore__ [aicore]",
            "#endif",
            "",
            f'extern "C" __aicore__ __attribute__((always_inline)) void {kernel.symbol_name}(__gm__ int64_t* args) {{',
            "    __gm__ float* lhs = reinterpret_cast<__gm__ float*>(args[0]);",
            "    __gm__ float* rhs = reinterpret_cast<__gm__ float*>(args[1]);",
            "    __gm__ float* out = reinterpret_cast<__gm__ float*>(args[2]);",
            "    int size = static_cast<int>(args[3]);",
            "    (void)size;",
            "",
            "    constexpr int kTRows_ = 128;",
            "    constexpr int kTCols_ = 128;",
            "    constexpr int vRows = 128;",
            "    constexpr int vCols = 128;",
            "",
            "    using DynShapeDim5 = Shape<1, 1, 1, vRows, vCols>;",
            "    using DynStridDim5 = Stride<1, 1, 1, kTCols_, 1>;",
            "    using GlobalData = GlobalTensor<float, DynShapeDim5, DynStridDim5>;",
            "    using TileData = Tile<TileType::Vec, float, kTRows_, kTCols_, BLayout::RowMajor, -1, -1>;",
            "",
            "    TileData lhsTile(vRows, vCols);",
            "    TileData rhsTile(vRows, vCols);",
            "    TileData dstTile(vRows, vCols);",
            "    TASSIGN(lhsTile, 0x0);",
            "    TASSIGN(rhsTile, 0x10000);",
            "    TASSIGN(dstTile, 0x20000);",
            "",
            "    GlobalData lhsGlobal(lhs);",
            "    GlobalData rhsGlobal(rhs);",
            "    GlobalData dstGlobal(out);",
            "",
            "    TLOAD(lhsTile, lhsGlobal);",
            "    TLOAD(rhsTile, rhsGlobal);",
            "    set_flag(PIPE_MTE2, PIPE_V, EVENT_ID0);",
            "    wait_flag(PIPE_MTE2, PIPE_V, EVENT_ID0);",
            f"    {math_intrinsic}(dstTile, lhsTile, rhsTile);",
            "    set_flag(PIPE_V, PIPE_MTE3, EVENT_ID0);",
            "    wait_flag(PIPE_V, PIPE_MTE3, EVENT_ID0);",
            "    TSTORE(dstGlobal, dstTile);",
            "}",
            "",
        )
    )


def _core_type_expr(core_type: str) -> str:
    if core_type == "aiv":
        return "CoreType::AIV"
    if core_type == "aic":
        return "CoreType::AIC"
    raise ValueError(f"Unsupported PTO core type: {core_type!r}")


def _project_relative(source_path: str) -> str:
    source = PurePosixPath(source_path)
    return source.relative_to(PTO_PROJECT_DIR).as_posix()


def _load_manifest(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text())


__all__ = [
    "PTO_CODEGEN_SCHEMA_ID",
    "PTO_PROJECT_DIR",
    "PTO_TOOLCHAIN_PATH",
    "PTO_TOOLCHAIN_SCHEMA_ID",
    "emit_package",
]
