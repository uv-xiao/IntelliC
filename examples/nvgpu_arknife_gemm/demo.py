from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
import htp.runtime as runtime_api


ARKNIFE_GEMM_PROGRAM: dict[str, Any] = {
    "entry": "gemm_tile",
    "ops": ["load", "mma", "store"],
}


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    """Compile an Arknife-inspired GEMM tile to the NV-GPU backend.

    The example is intentionally aligned with Arknife's explicit hardware
    thinking: a block-level tile kernel, an explicit Ampere profile, and a
    source-first `.cu` package contract.
    """

    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=dict(ARKNIFE_GEMM_PROGRAM),
    )
    return {
        "package_dir": package.package_dir.as_posix(),
        "target": {
            "backend": package.target.backend,
            "option": package.target.option,
        },
        "manifest_path": (package.package_dir / "manifest.json").as_posix(),
    }


def replay_latest_stage(output_dir: Path | str) -> dict[str, Any]:
    """Replay the latest Python stage for the NV-GPU package."""

    package_dir = Path(output_dir)
    session = bind(package_dir).load(mode="sim")
    stage_id = session.manifest["stages"]["current"]
    result = session.replay(stage_id, trace="basic")
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
    }


def run_sim_package(output_dir: Path | str) -> dict[str, Any]:
    """Run the package in `sim` using a registered replay kernel handler."""

    # Register a deterministic handler on the shared replay runtime so the
    # example can execute without CUDA or `nvcc`.
    runtime = runtime_api.default_runtime()
    runtime.register_kernel(
        "gemm_tile.kernel0",
        lambda *, args, mode, artifacts, trace=None: {
            "args": list(args),
            "mode": mode,
            "trace": trace,
            "artifacts": dict(artifacts),
        },
    )
    result = bind(Path(output_dir)).load(mode="sim").run("gemm_tile", trace="basic")
    return {
        "ok": result.ok,
        "entry": result.entry,
        "result": result.result,
        "diagnostics": list(result.diagnostics),
        "runtime_hint": "register the same handler on htp.runtime.default_runtime() in an interactive session",
    }


def build_device_package(output_dir: Path | str) -> dict[str, Any]:
    """Materialize `.ptx`/`.cubin` if `nvcc` is available."""

    result = bind(Path(output_dir)).build(mode="device")
    return {
        "ok": result.ok,
        "mode": result.mode,
        "built_outputs": list(result.built_outputs),
        "diagnostics": list(result.diagnostics),
    }


def run_device_package(output_dir: Path | str) -> dict[str, Any]:
    """Attempt the real device path through the CUDA driver adapter."""

    result = bind(Path(output_dir)).load(mode="device").run("gemm_tile")
    return {
        "ok": result.ok,
        "entry": result.entry,
        "result": result.result,
        "diagnostics": list(result.diagnostics),
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    """Run the full NV-GPU example workflow and return a JSON-friendly summary."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    # The device path is optional; the example still proves the full contract
    # through compile + replay + sim package execution on any developer machine.
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    sim_summary = run_sim_package(output_path)
    device_build_summary = build_device_package(output_path)
    device_run_summary = run_device_package(output_path) if device_build_summary["ok"] else None
    return {
        "example": "nvgpu_arknife_gemm",
        "compile": compile_summary,
        "replay": replay_summary,
        "sim_run": sim_summary,
        "device_build": device_build_summary,
        "device_run": device_run_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "nvgpu_arknife_gemm")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
