from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from htp.schemas import MANIFEST_SCHEMA_ID

from .lower import PTOCodegenPlan, lower_program

PTO_CODEGEN_SCHEMA_ID = "htp.pto.codegen.v1"
PTO_TOOLCHAIN_SCHEMA_ID = "htp.pto.toolchain.v1"
PTO_PROJECT_DIR = PurePosixPath("codegen/pto")
PTO_TOOLCHAIN_PATH = PurePosixPath("build/toolchain.json")


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
    outputs.update(
        {
            "kernel_config": (PTO_PROJECT_DIR / "kernel_config.py").as_posix(),
            "pto_codegen_index": (PTO_PROJECT_DIR / "pto_codegen.json").as_posix(),
            "toolchain_manifest": PTO_TOOLCHAIN_PATH.as_posix(),
        }
    )
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
        kernel_path.write_text(_kernel_source(plan, kernel))

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
        "env": {
            "PTO_ISA_ROOT": "auto",
        },
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
    core_type_expr = _core_type_expr(plan.kernels[0].core_type)
    return "\n".join(
        (
            '#include "runtime.h"',
            "#include <cstdint>",
            "#include <iostream>",
            "",
            "// PTO host_build_graph orchestration ABI expected by pto-runtime:",
            '//   extern "C" int entry(Runtime*, uint64_t*, int)',
            "// The v1 package emits a minimal smoke task so HTP can prove the",
            "// real a2a3sim execution path before richer tensor marshaling lands.",
            f'extern "C" int {plan.orchestration.function_name}(Runtime* runtime, uint64_t* args, int arg_count) {{',
            "    (void)args;",
            "    (void)arg_count;",
            "    if (runtime == nullptr) {",
            "        std::cerr << \"orchestration received null runtime\" << '\\n';",
            "        return -1;",
            "    }",
            f"    const int task0 = runtime->add_task(nullptr, 0, {plan.kernels[0].func_id}, {core_type_expr});",
            "    if (task0 < 0) {",
            "        std::cerr << \"failed to add PTO smoke task\" << '\\n';",
            "        return -1;",
            "    }",
            "    runtime->print_runtime();",
            "    return 0;",
            "}",
            "",
        )
    )


def _kernel_source(plan: PTOCodegenPlan, kernel: Any) -> str:
    del plan
    return "\n".join(
        (
            "#include <cstdint>",
            "",
            "#ifndef __gm__",
            "#define __gm__",
            "#endif",
            "",
            "#ifndef __aicore__",
            "#define __aicore__",
            "#endif",
            "",
            '// PTO simulation kernels are loaded with dlopen+dlsym("kernel_entry").',
            f'extern "C" __aicore__ __attribute__((always_inline)) void {kernel.symbol_name}(__gm__ int64_t* args) {{',
            "    (void)args;",
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
