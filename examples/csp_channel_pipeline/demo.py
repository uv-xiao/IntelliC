from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.csp import channel, process
from htp.csp import program as csp_program

CSP_PIPELINE_PROGRAM: dict[str, Any] = csp_program(
    entry="pipeline_demo",
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
    channels=[channel("tiles", dtype="f32", capacity=2)],
    processes=[
        process("producer", task_id="p0", kernel="gemm_tile", puts=[{"channel": "tiles", "count": 1}]),
        process("consumer", task_id="p1", kernel="gemm_tile", gets=[{"channel": "tiles", "count": 1}]),
    ],
)


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=dict(CSP_PIPELINE_PROGRAM),
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
    effects = json.loads((package_dir / "ir" / "stages" / stage_id / "effects.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "effects": effects,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    return {
        "example": "csp_channel_pipeline",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "csp_channel_pipeline")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
