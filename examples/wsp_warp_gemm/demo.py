from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.kernel import buffer, kernel, scalar, store
from htp.wsp import bind as wsp_bind
from htp.wsp import pipeline as wsp_pipeline
from htp.wsp import program as wsp_program
from htp.wsp import resources as wsp_resources
from htp.wsp import specialize as wsp_specialize
from htp.wsp import task as wsp_task
from htp.wsp import tile as wsp_tile


@kernel
def gemm_tile(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    """Warp-scheduled GEMM tile expressed as direct Python math."""

    store(C, A @ B)


@wsp_program(
    target="nvgpu-ampere",
    tile=wsp_tile(block=(32, 64, 16)),
    bind=wsp_bind(grid="block", lane="warp"),
    pipeline=wsp_pipeline(depth=2, buffering="double"),
    resources=wsp_resources(num_warps=4),
    specialize=wsp_specialize(operator="matmul"),
)
def warp_specialized_gemm(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C_partial: buffer(dtype="f32", shape=("M", "N"), role="output"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    load_warp = wsp_task(gemm_tile, A, B, C_partial, M, N, K, task_id="load_warp")
    compute_warp = wsp_task(gemm_tile, A, B, C_partial, M, N, K, after=load_warp, task_id="compute_warp")
    wsp_task(gemm_tile, A, B, C, M, N, K, after=compute_warp, task_id="store_warp")


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=warp_specialized_gemm,
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
