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
from htp.wsp import schedule as wsp_schedule
from htp.wsp import specialize as wsp_specialize
from htp.wsp import task as wsp_task
from htp.wsp import tile as wsp_tile


@kernel
def pipelined_gemm(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    """LittleKernel-inspired GEMM kernel body expressed as plain Python."""

    store(C, A @ B)


LITTLEKERNEL_GEMM_PROGRAM: dict[str, Any] = wsp_program(
    entry="pipelined_gemm",
    target="nvgpu-ampere",
    kernel=pipelined_gemm,
    tasks=[wsp_task(pipelined_gemm, "A", "B", "C", "M", "N", "K", task_id="tile_main")],
    schedule=wsp_schedule(
        tile=wsp_tile(block=(128, 256, 64)),
        bind=wsp_bind(grid="block", lane="warp"),
        pipeline=wsp_pipeline(depth=3, buffering="double"),
        resources=wsp_resources(num_warps=8),
        specialize=wsp_specialize(operator="matmul"),
    ),
)


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=dict(LITTLEKERNEL_GEMM_PROGRAM),
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
