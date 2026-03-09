from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

import htp.runtime as runtime_api
from htp import ark, bind, compile_program


@ark.build(target="nvgpu-ampere", hardware=ark.ampere())
def ampere_mainloop_gemm():
    """Ampere GEMM mainloop written with the Arknife-style HTP surface."""

    A = ark.tensor("A", dtype="f32", shape=("M", "K"), role="input", memory="global")
    B = ark.tensor("B", dtype="f32", shape=("K", "N"), role="input", memory="global")
    C = ark.tensor("C", dtype="f32", shape=("M", "N"), role="output", memory="global")
    AS = ark.tensor("AS", dtype="f32", shape=("BM", "BK"), memory="shared")
    BS = ark.tensor("BS", dtype="f32", shape=("BK", "BN"), memory="shared")
    AR = ark.tensor("AR", dtype="f32", shape=("WM", "WK"), memory="register")
    BR = ark.tensor("BR", dtype="f32", shape=("WK", "WN"), memory="register")
    CR = ark.tensor("CR", dtype="f32", shape=("WM", "WN"), memory="register")

    block_m = ark.axis("block_m", 2)
    block_n = ark.axis("block_n", 2)
    warp_m = ark.axis("warp_m", 2)
    warp_n = ark.axis("warp_n", 2)
    k_outer = ark.axis("k_outer", 4)

    with ark.spatial("block", block_m, block_n, swizzle=[8, None]):
        with ark.pipeline(k_outer, stages=3):
            ark.cp_async(AS, A, channel="shared_pipe")
            ark.cp_async(BS, B, channel="shared_pipe")
            with ark.spatial("warp", warp_m, warp_n):
                ark.ldmatrix(AR, AS)
                ark.ldmatrix(BR, BS)
                ark.mma_sync(CR, AR, BR, accum=CR, shape=(16, 8, 16))
        ark.commit(C, CR)
    return A, B, C


def make_inputs(
    m: int = 64, n: int = 64, k: int = 64
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
        program=ampere_mainloop_gemm,
    )
    codegen_index_path = package.package_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json"
    codegen_index = json.loads(codegen_index_path.read_text())
    return {
        "package_dir": package.package_dir.as_posix(),
        "target": {"backend": package.target.backend, "option": package.target.option},
        "manifest_path": (package.package_dir / "manifest.json").as_posix(),
        "instruction_plan": codegen_index["kernels"][0]["instruction_plan"],
    }


def replay_latest_stage(output_dir: Path | str) -> dict[str, Any]:
    package_dir = Path(output_dir)
    session = bind(package_dir).load(mode="sim")
    stage_id = session.manifest["stages"]["current"]
    result = session.replay(stage_id, trace="basic")
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "schedule": result.result.get("schedule", {}),
        "layout": result.result.get("layout", {}),
    }


def run_sim_package(output_dir: Path | str) -> dict[str, Any]:
    runtime = runtime_api.default_runtime()

    def _gemm_handler(*, args, mode, artifacts, trace=None):
        del mode, artifacts, trace
        a, b, c, m, n, k = args
        c[:, :] = np.matmul(a.reshape(m, k), b.reshape(k, n))
        return {"shape": [m, n], "checksum": float(c.sum())}

    runtime.register_kernel("ampere_mainloop_gemm.kernel0", _gemm_handler)
    a, b, c, m, n, k = make_inputs()
    result = (
        bind(Path(output_dir))
        .load(mode="sim")
        .run(
            "ampere_mainloop_gemm",
            args=(a, b, c, m, n, k),
            trace="basic",
        )
    )
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
    result = (
        bind(Path(output_dir))
        .load(mode="device")
        .run(
            "ampere_mainloop_gemm",
            args=(a, b, c, m, n, k),
        )
    )
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
