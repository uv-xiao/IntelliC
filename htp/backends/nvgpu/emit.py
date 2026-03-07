from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from htp.schemas import MANIFEST_SCHEMA_ID

from .lower import NVGPUCodegenPlan, lower_program

NVGPU_CODEGEN_SCHEMA_ID = "htp.nvgpu.codegen.v1"
NVGPU_TOOLCHAIN_SCHEMA_ID = "htp.nvgpu.toolchain.v1"
NVGPU_PROJECT_DIR = PurePosixPath("codegen/nvgpu")
NVGPU_TOOLCHAIN_PATH = PurePosixPath("build/toolchain.json")


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
    outputs.update(
        {
            "nvgpu_codegen_index": (NVGPU_PROJECT_DIR / "nvgpu_codegen.json").as_posix(),
            "toolchain_manifest": NVGPU_TOOLCHAIN_PATH.as_posix(),
        }
    )
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
        kernel_path.write_text(_kernel_source(plan, kernel))

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
    return "\n".join(
        (
            "from htp.runtime import call_kernel, default_runtime",
            "",
            f"def {plan.launch.function_name}(*args, mode=\"sim\", trace=None, runtime=None):",
            "    resolved_runtime = default_runtime() if runtime is None else runtime",
            "    return call_kernel(",
            f"        \"{kernel.kernel_id}\",",
            "        args=args,",
            "        mode=mode,",
            "        trace=trace,",
            "        runtime=resolved_runtime,",
            "        artifacts={",
            f"            \"backend\": \"{plan.backend}\",",
            f"            \"variant\": \"{plan.variant}\",",
            f"            \"hardware_profile\": \"{plan.hardware_profile}\",",
            f"            \"kernel_source\": \"{kernel.source}\",",
            "        },",
            "    )",
            "",
        )
    )


def _kernel_source(plan: NVGPUCodegenPlan, kernel: Any) -> str:
    return "\n".join(
        (
            "#include <cuda_runtime.h>",
            "",
            f"extern \"C\" __global__ void {kernel.func_id}() {{",
            f"  // profile: {plan.profile}",
            "  (void)threadIdx.x;",
            "}",
            "",
        )
    )


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
