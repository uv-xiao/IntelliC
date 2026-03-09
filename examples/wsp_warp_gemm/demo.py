from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.wsp import program as wsp_program
from htp.wsp import schedule as wsp_schedule
from htp.wsp import workload as wsp_workload

WSP_GEMM_PROGRAM: dict[str, Any] = wsp_program(
    entry="gemm_tile",
    target={"backend": "nvgpu", "option": "ampere"},
    kernel={
        "name": "gemm_tile",
        "args": [
            {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
            {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
            {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
            {"name": "M", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
            {"name": "N", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
            {"name": "K", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
        ],
        "ops": [
            {"op": "matmul", "lhs": "A", "rhs": "B", "out": "C", "m": "M", "n": "N", "k": "K", "dtype": "f32"}
        ],
    },
    workload=wsp_workload(
        entry="gemm_tile",
        tasks=[
            {
                "task_id": "task0",
                "kind": "kernel_call",
                "kernel": "gemm_tile",
                "args": ["A", "B", "C", "M", "N", "K"],
            }
        ],
    ),
    schedule=wsp_schedule(
        tile={"block": [32, 64, 16]},
        bind={"grid": "block", "lane": "warp"},
        pipeline={"depth": 2, "buffering": "double"},
        resources={"num_warps": 4},
        specialize={"operator": "matmul"},
    ),
)


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=dict(WSP_GEMM_PROGRAM),
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
        "example": "wsp_warp_gemm",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "wsp_warp_gemm")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
