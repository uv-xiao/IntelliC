from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from htp import bind, compile_program
from htp.kernel import buffer, kernel, scalar, store


@kernel
def vector_add(
    lhs: buffer(dtype="f32", shape=("size",), role="input"),
    rhs: buffer(dtype="f32", shape=("size",), role="input"),
    out: buffer(dtype="f32", shape=("size",), role="output"),
    size: scalar(dtype="i32", role="shape"),
) -> None:
    """Host reference backend example using the native HTP kernel surface."""

    store(out, lhs + rhs)


def make_inputs(size: int = 128) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    lhs = np.arange(size, dtype=np.float32)
    rhs = np.arange(size, dtype=np.float32) * 2.0
    out = np.zeros(size, dtype=np.float32)
    return lhs, rhs, out, size


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(package_dir=Path(output_dir), target="cpu_ref", program=vector_add)
    return {
        "package_dir": package.package_dir.as_posix(),
        "target": {"backend": package.target.backend, "option": package.target.option},
        "manifest_path": (package.package_dir / "manifest.json").as_posix(),
    }


def replay_latest_stage(output_dir: Path | str) -> dict[str, Any]:
    session = bind(Path(output_dir)).load(mode="sim")
    stage_id = session.manifest["stages"]["current"]
    replay = session.replay(stage_id, trace="basic")
    return {
        "ok": replay.ok,
        "stage_id": stage_id,
        "entry": replay.entry,
        "diagnostics": replay.diagnostics,
    }


def build_package(output_dir: Path | str) -> dict[str, Any]:
    result = bind(Path(output_dir)).build(mode="sim")
    return {
        "ok": result.ok,
        "mode": result.mode,
        "built_outputs": list(result.built_outputs),
        "diagnostics": list(result.diagnostics),
    }


def run_package(output_dir: Path | str) -> dict[str, Any]:
    lhs, rhs, out, size = make_inputs()
    result = bind(Path(output_dir)).load(mode="sim").run("vector_add", args=(lhs, rhs, out, size))
    return {
        "ok": result.ok,
        "entry": result.entry,
        "diagnostics": list(result.diagnostics),
        "result": result.result,
        "max_abs_error": float(np.max(np.abs(out - (lhs + rhs)))),
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    build_summary = build_package(output_path)
    run_summary = run_package(output_path)
    return {
        "example": "cpu_ref_vector_add",
        "compile": compile_summary,
        "replay": replay_summary,
        "build": build_summary,
        "run": run_summary,
    }


def main() -> None:
    print(json.dumps(run_demo(Path("artifacts") / "cpu_ref_vector_add"), indent=2))


if __name__ == "__main__":
    main()
