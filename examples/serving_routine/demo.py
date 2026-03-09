from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program

SERVING_ROUTINE_PROGRAM: dict[str, Any] = {
    "entry": "serving_routine",
    "target": {"backend": "nvgpu", "option": "ampere"},
    "kernel": {
        "name": "decode_step",
        "args": [
            {"name": "hidden", "kind": "buffer", "dtype": "f32", "shape": ["B", "H"], "role": "input"},
            {"name": "weights", "kind": "buffer", "dtype": "f32", "shape": ["H", "H"], "role": "input"},
            {"name": "next_hidden", "kind": "buffer", "dtype": "f32", "shape": ["B", "H"], "role": "output"},
            {"name": "B", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
            {"name": "H", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
        ],
        "ops": [
            {
                "op": "matmul",
                "lhs": "hidden",
                "rhs": "weights",
                "out": "next_hidden",
                "m": "B",
                "n": "H",
                "k": "H",
                "dtype": "f32",
            }
        ],
    },
    "workload": {
        "entry": "serving_routine",
        "tasks": [
            {
                "task_id": "prefill",
                "kind": "kernel_call",
                "kernel": "decode_step",
                "args": ["hidden", "weights", "next_hidden", "B", "H"],
            },
            {
                "task_id": "decode",
                "kind": "kernel_call",
                "kernel": "decode_step",
                "args": ["next_hidden", "weights", "next_hidden", "B", "H"],
            },
            {
                "task_id": "writeback",
                "kind": "kernel_call",
                "kernel": "decode_step",
                "args": ["next_hidden", "weights", "next_hidden", "B", "H"],
            },
        ],
        "channels": [],
        "dependencies": [
            {"src": "prefill", "dst": "decode"},
            {"src": "decode", "dst": "writeback"},
        ],
    },
}


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=dict(SERVING_ROUTINE_PROGRAM),
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
    replay = session.replay(stage_id, trace="basic")
    workload_ir = json.loads((package_dir / "ir" / "stages" / stage_id / "workload_ir.json").read_text())
    return {
        "ok": replay.ok,
        "stage_id": stage_id,
        "entry": replay.entry,
        "diagnostics": replay.diagnostics,
        "workload_ir": workload_ir,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return {
        "example": "serving_routine",
        "compile": compile_example(output_path),
        "replay": replay_latest_stage(output_path),
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "serving_routine")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
