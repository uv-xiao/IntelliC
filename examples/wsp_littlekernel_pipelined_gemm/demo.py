from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.kernel import async_copy, barrier, buffer, kernel, mma, scalar, store
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

    a_stage0 = async_copy(A, dtype="f32", memory_space="shared")
    b_stage0 = async_copy(B, dtype="f32", memory_space="shared")
    barrier()
    mma(a_stage0, b_stage0, out="accum0", m=M, n=N, k=K, dtype="f32")

    a_stage1 = async_copy(A, dtype="f32", memory_space="shared")
    b_stage1 = async_copy(B, dtype="f32", memory_space="shared")
    barrier()
    accum1 = mma(a_stage1, b_stage1, m=M, n=N, k=K, dtype="f32")
    store(C, accum1)


@wsp_program(target="nvgpu-ampere", kernel=pipelined_mainloop_gemm)
def littlekernel_pipelined_gemm(w) -> None:
    (
        w.launch(pipelined_mainloop_gemm, "A", "B", "C", "M", "N", "K", task_id="tile_main")
        .tile(block=(128, 256, 64))
        .bind(grid="block", lane="warp")
        .pipeline(depth=3, buffering="double")
        .resources(num_warps=8)
        .specialize(operator="pipelined_mainloop", stage_plan="load0->mma0->load1->mma1")
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
    schedule = json.loads((package_dir / "ir" / "stages" / stage_id / "schedule.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "schedule": schedule,
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
