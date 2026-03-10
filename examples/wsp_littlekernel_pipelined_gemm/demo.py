from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.kernel import (
    async_copy,
    barrier,
    buffer,
    kernel,
    mma,
    region,
    registers,
    scalar,
    shared_array,
    store,
    unroll,
)
from htp.wsp import program as wsp_program


@kernel
def pipelined_mainloop_gemm(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    """Pipelined GEMM mainloop with double-buffered shared-memory stages."""

    a_stages = shared_array("a_stage", count=2, dtype="f32", shape=("M", "K"))
    b_stages = shared_array("b_stage", count=2, dtype="f32", shape=("K", "N"))
    partials = []
    accum = registers("acc", dtype="f32", shape=("M", "N"))

    for stage in unroll(range(2), name="stage"):
        with region("mainloop_stage", phase="steady"):
            async_copy(A, target=a_stages[stage], dtype="f32")
            async_copy(B, target=b_stages[stage], dtype="f32")
            barrier()
            partial = mma(a_stages[stage], b_stages[stage], m=M, n=N, k=K, dtype="f32")
            partials.append(partial)
    accum = partials[0] + partials[1]
    store(C, accum)


@wsp_program(target="nvgpu-ampere", kernel=pipelined_mainloop_gemm)
def littlekernel_pipelined_gemm(w) -> None:
    prefetch_tiles = (
        w.launch(pipelined_mainloop_gemm, "A", "B", "C", "M", "N", "K", task_id="prefetch_tiles")
        .role("producer")
        .tile(block=(128, 256, 64))
        .bind(grid="block", lane="warp")
        .pipeline(depth=3, buffering="double")
        .resources(num_warps=8)
        .prologue("cp_async(stage0:A)", "cp_async(stage0:B)", "cp_async(stage1:A)", "cp_async(stage1:B)")
    )
    steady_tiles = (
        w.mainloop(pipelined_mainloop_gemm, "A", "B", "C", "M", "N", "K", task_id="steady_tiles")
        .after(prefetch_tiles)
        .tile(block=(128, 256, 64))
        .bind(grid="block", lane="warp")
        .pipeline(depth=3, buffering="double")
        .resources(num_warps=8)
        .role("consumer")
        .prologue("ldmatrix(stage0)", "ldmatrix(stage1)")
        .steady("mma_sync(stage0)", "mma_sync(stage1)", "advance_pipeline")
    )
    (
        w.launch(pipelined_mainloop_gemm, "A", "B", "C", "M", "N", "K", task_id="writeback_tiles")
        .after(steady_tiles)
        .tile(block=(128, 256, 64))
        .bind(grid="block", lane="warp")
        .pipeline(depth=3, buffering="double")
        .resources(num_warps=8)
        .role("epilogue")
        .epilogue("store(C)")
        .specialize(operator="pipelined_mainloop", stage_plan="prefetch_tiles->steady_tiles->writeback_tiles")
    )


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=littlekernel_pipelined_gemm,
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
    kernel_ir = json.loads((package_dir / "ir" / "stages" / stage_id / "kernel_ir.json").read_text())
    schedule = json.loads((package_dir / "ir" / "stages" / stage_id / "schedule.json").read_text())
    workload_ir = json.loads((package_dir / "ir" / "stages" / stage_id / "workload_ir.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "kernel_ir": kernel_ir,
        "schedule": schedule,
        "workload_ir": workload_ir,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    return {
        "example": "wsp_littlekernel_pipelined_gemm",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "wsp_littlekernel_pipelined_gemm")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
