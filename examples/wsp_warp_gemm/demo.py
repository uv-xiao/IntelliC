from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.kernel import async_copy, barrier, buffer, kernel, mma, scalar, store
from htp.wsp import program as wsp_program


@kernel
def warp_mainloop_tile(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    """Warp-level GEMM mainloop with staged copies and tensor-core math."""

    a_shared = async_copy(A, dtype="f32", memory_space="shared")
    b_shared = async_copy(B, dtype="f32", memory_space="shared")
    barrier()
    accum0 = mma(a_shared, b_shared, m=M, n=N, k=K, dtype="f32")
    accum1 = mma(a_shared, b_shared, m=M, n=N, k=K, dtype="f32")
    store(C, accum0 + accum1)


@wsp_program(target="nvgpu-ampere", kernel=warp_mainloop_tile)
def warp_gemm(w) -> None:
    load_tiles = (
        w.launch(warp_mainloop_tile, "A", "B", "C", "M", "N", "K", task_id="load_tiles")
        .role("producer")
        .tile(block=(64, 128, 32))
        .bind(grid="block", lane="warp")
        .pipeline(depth=3, buffering="double")
        .resources(num_warps=4)
        .prologue("cp_async(A->shared)", "cp_async(B->shared)")
    )
    mma_tiles = (
        w.mainloop(warp_mainloop_tile, "A", "B", "C", "M", "N", "K", task_id="mma_tiles")
        .after(load_tiles)
        .tile(block=(64, 128, 32))
        .bind(grid="block", lane="warp")
        .pipeline(depth=3, buffering="double")
        .resources(num_warps=4)
        .role("consumer")
        .steady("barrier", "mma_sync", "accumulate")
    )
    (
        w.launch(warp_mainloop_tile, "A", "B", "C", "M", "N", "K", task_id="store_tiles")
        .after(mma_tiles)
        .tile(block=(64, 128, 32))
        .bind(grid="block", lane="warp")
        .pipeline(depth=3, buffering="double")
        .resources(num_warps=4)
        .role("epilogue")
        .epilogue("store(C)")
        .specialize(operator="tensor_core_mainloop", stage_plan="load_tiles->mma_tiles->store_tiles")
    )


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=warp_gemm,
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
    schedule = json.loads((package_dir / "ir" / "stages" / stage_id / "schedule.json").read_text())
    workload_ir = json.loads((package_dir / "ir" / "stages" / stage_id / "workload_ir.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "schedule": schedule,
        "workload_ir": workload_ir,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    return {
        "example": "wsp_warp_gemm",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "wsp_warp_gemm")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
