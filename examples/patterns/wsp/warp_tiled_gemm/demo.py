"""Warp-tiled GEMM example on the traced WSP surface.

This is the smallest HTP example that still preserves the semantic point of a
warp-partitioned GEMM block: one CTA owns a block tile and four warp-owned
microtiles cover a `2 x 2` output grid.
"""

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
def gemm_microtile(
    A: buffer(dtype="f32", shape=("TM", "TK"), role="input"),
    B: buffer(dtype="f32", shape=("TK", "TN"), role="input"),
    C: buffer(dtype="f32", shape=("TM", "TN"), role="output"),
    TM: scalar(dtype="i32", role="shape"),
    TN: scalar(dtype="i32", role="shape"),
    TK: scalar(dtype="i32", role="shape"),
) -> None:
    """One warp-owned GEMM microtile."""

    store(C, A @ B)


@wsp_program(
    target="nvgpu-ampere",
    tile=wsp_tile(block=(32, 64, 16)),
    bind=wsp_bind(grid="block", lane="warp"),
    pipeline=wsp_pipeline(depth=2, buffering="double"),
    resources=wsp_resources(num_warps=4),
    specialize=wsp_specialize(operator="matmul"),
)
def warp_tiled_gemm(
    A_row0: buffer(dtype="f32", shape=("TM", "TK"), role="input"),
    A_row1: buffer(dtype="f32", shape=("TM", "TK"), role="input"),
    B_col0: buffer(dtype="f32", shape=("TK", "TN"), role="input"),
    B_col1: buffer(dtype="f32", shape=("TK", "TN"), role="input"),
    C_00: buffer(dtype="f32", shape=("TM", "TN"), role="output"),
    C_01: buffer(dtype="f32", shape=("TM", "TN"), role="output"),
    C_10: buffer(dtype="f32", shape=("TM", "TN"), role="output"),
    C_11: buffer(dtype="f32", shape=("TM", "TN"), role="output"),
    TM: scalar(dtype="i32", role="shape"),
    TN: scalar(dtype="i32", role="shape"),
    TK: scalar(dtype="i32", role="shape"),
) -> None:
    """One CTA-level `2 x 2` output tile grid.

    The program is intentionally flat: the meaningful content is tile
    ownership plus launch schedule, not a fake sequence of phases.
    """

    wsp_task(gemm_microtile, A_row0, B_col0, C_00, TM, TN, TK, task_id="tile_00")
    wsp_task(gemm_microtile, A_row0, B_col1, C_01, TM, TN, TK, task_id="tile_01")
    wsp_task(gemm_microtile, A_row1, B_col0, C_10, TM, TN, TK, task_id="tile_10")
    wsp_task(gemm_microtile, A_row1, B_col1, C_11, TM, TN, TK, task_id="tile_11")


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=warp_tiled_gemm,
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
        "example": "patterns.wsp.warp_tiled_gemm",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "patterns" / "wsp" / "warp_tiled_gemm")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
