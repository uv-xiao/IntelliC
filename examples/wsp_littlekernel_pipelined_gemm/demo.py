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

BLOCK_K = 16


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

    a_stages = shared_array("a_stage", count=2, dtype="f32", shape=("M", BLOCK_K))
    b_stages = shared_array("b_stage", count=2, dtype="f32", shape=(BLOCK_K, "N"))
    partials = []
    registers("acc", dtype="f32", shape=("M", "N"))

    for stage in unroll(range(2), name="stage"):
        k0 = stage * BLOCK_K
        a_view = A[:, k0 : k0 + BLOCK_K]
        b_view = B[k0 : k0 + BLOCK_K, :]
        with region("mainloop_stage", phase="steady"):
            async_copy(a_view, target=a_stages[stage], dtype="f32")
            async_copy(b_view, target=b_stages[stage], dtype="f32")
            barrier()
            partial = mma(a_stages[stage], b_stages[stage], m=M, n=N, k=BLOCK_K, dtype="f32")
            partials.append(partial)
    store(C, partials[0] + partials[1])


@wsp_program(target="nvgpu-ampere", kernel=pipelined_mainloop_gemm)
def littlekernel_pipelined_gemm(w) -> None:
    with w.defaults(
        tile={"block": (128, 256, 64)},
        bind={"grid": "block", "lane": "warp"},
        pipeline={"depth": 3, "buffering": "double"},
        resources={"num_warps": 8},
    ):
        prefetch_tiles = w.launch(task_id="prefetch_tiles").role("producer")
        prefetch_tiles.prologue().step("cp_async", source=w.args.A, target="a_stage0")
        prefetch_tiles.prologue().step("cp_async", source=w.args.B, target="b_stage0")
        prefetch_tiles.prologue().step("cp_async", source=w.args.A, target="a_stage1")
        prefetch_tiles.prologue().step("cp_async", source=w.args.B, target="b_stage1")

        steady_tiles = w.mainloop(task_id="steady_tiles").after(prefetch_tiles).role("consumer")
        steady_tiles.prologue().step("ldmatrix", source="a_stage")
        steady_tiles.prologue().step("ldmatrix", source="b_stage")
        steady_tiles.steady().step("mma_sync", stage=0)
        steady_tiles.steady().step("mma_sync", stage=1)
        steady_tiles.steady().step("advance_pipeline")

        epilogue_tiles = w.launch(task_id="epilogue_tiles").after(steady_tiles).role("reducer")
        epilogue_tiles.epilogue().step("reduce_accumulators", source="acc")
        epilogue_tiles.epilogue().step("convert_output", target=w.args.C)

        writeback_tiles = w.launch(task_id="writeback_tiles").after(epilogue_tiles).role("epilogue")
        writeback_tiles.epilogue().step("store", target=w.args.C)
        writeback_tiles.specialize(
            operator="pipelined_mainloop",
            stage_plan="prefetch_tiles->steady_tiles->epilogue_tiles->writeback_tiles",
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
    state = json.loads((package_dir / "ir" / "stages" / stage_id / "state.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "kernel_ir": state["items"]["kernel_ir"],
        "schedule": state["aspects"]["schedule"],
        "workload_ir": state["items"]["workload_ir"],
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
