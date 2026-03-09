from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

import htp.runtime as runtime_api
from htp import bind, compile_program
from htp.kernel import buffer, kernel, scalar, store


@kernel
def gemm_tile(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    """Arknife-inspired GEMM tile expressed as ordinary Python."""

    store(C, A @ B)


def make_inputs(
    m: int = 32, n: int = 32, k: int = 32
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int, int]:
    rng = np.random.default_rng(0)
    a = rng.standard_normal((m, k), dtype=np.float32)
    b = rng.standard_normal((k, n), dtype=np.float32)
    c = np.zeros((m, n), dtype=np.float32)
    return a, b, c, m, n, k


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=gemm_tile,
    )
    return {
        "package_dir": package.package_dir.as_posix(),
        "target": {"backend": package.target.backend, "option": package.target.option},
        "manifest_path": (package.package_dir / "manifest.json").as_posix(),
    }


def replay_latest_stage(output_dir: Path | str) -> dict[str, Any]:
    package_dir = Path(output_dir)
    session = bind(package_dir).load(mode="sim")
    stage_id = session.manifest["stages"]["current"]
    result = session.replay(stage_id, trace="basic")
    return {"ok": result.ok, "stage_id": stage_id, "entry": result.entry, "diagnostics": result.diagnostics}


def run_sim_package(output_dir: Path | str) -> dict[str, Any]:
    runtime = runtime_api.default_runtime()

    def _gemm_handler(*, args, mode, artifacts, trace=None):
        del mode, artifacts, trace
        a, b, c, m, n, k = args
        c[:, :] = np.matmul(a.reshape(m, k), b.reshape(k, n))
        return {"shape": [m, n], "checksum": float(c.sum())}

    runtime.register_kernel("gemm_tile.kernel0", _gemm_handler)
    a, b, c, m, n, k = make_inputs()
    result = bind(Path(output_dir)).load(mode="sim").run("gemm_tile", args=(a, b, c, m, n, k), trace="basic")
    reference = a @ b
    return {
        "ok": result.ok,
        "entry": result.entry,
        "result": result.result,
        "diagnostics": list(result.diagnostics),
        "max_abs_error": float(np.max(np.abs(c - reference))),
    }


def build_device_package(output_dir: Path | str) -> dict[str, Any]:
    result = bind(Path(output_dir)).build(mode="device")
    return {
        "ok": result.ok,
        "mode": result.mode,
        "built_outputs": list(result.built_outputs),
        "diagnostics": list(result.diagnostics),
    }


def run_device_package(output_dir: Path | str) -> dict[str, Any]:
    a, b, c, m, n, k = make_inputs()
    result = bind(Path(output_dir)).load(mode="device").run("gemm_tile", args=(a, b, c, m, n, k))
    reference = a @ b
    max_abs_error = float(np.max(np.abs(c - reference)))
    return {
        "ok": result.ok and max_abs_error < 1e-4,
        "entry": result.entry,
        "result": result.result,
        "diagnostics": list(result.diagnostics),
        "max_abs_error": max_abs_error,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    sim_summary = run_sim_package(output_path)
    device_build_summary = build_device_package(output_path)
    device_run_summary = run_device_package(output_path) if device_build_summary["ok"] else None
    return {
        "example": "nvgpu.arknife_gemm",
        "compile": compile_summary,
        "replay": replay_summary,
        "sim_run": sim_summary,
        "device_build": device_build_summary,
        "device_run": device_run_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "nvgpu" / "arknife_gemm")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
