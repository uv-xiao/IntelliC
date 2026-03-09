from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from htp import bind, compile_program
from htp.kernel import buffer, kernel, scalar, sigmoid, store


@kernel
def swiglu(
    gate: buffer(dtype="f32", shape=("size",), role="input"),
    up: buffer(dtype="f32", shape=("size",), role="input"),
    out: buffer(dtype="f32", shape=("size",), role="output"),
    size: scalar(dtype="i32", role="shape"),
) -> None:
    """PyPTO-calibrated fused activation: Swish(gate) * up."""

    gate_sigmoid = sigmoid(gate)
    store(out, gate * gate_sigmoid * up)


def make_inputs(size: int = 32 * 128) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    gate = rng.standard_normal(size, dtype=np.float32)
    up = rng.standard_normal(size, dtype=np.float32)
    out = np.zeros(size, dtype=np.float32)
    expected = gate * (1.0 / (1.0 + np.exp(-gate))) * up
    return gate, up, out, expected


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="pto-a2a3sim",
        program=swiglu,
    )
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
    gate, up, out, expected = make_inputs()
    result = bind(Path(output_dir)).load(mode="sim").run("swiglu", args=(gate, up, out, gate.size))
    max_abs_error = float(np.max(np.abs(out - expected))) if result.ok else None
    return {
        "ok": result.ok,
        "entry": result.entry,
        "result": result.result,
        "diagnostics": list(result.diagnostics),
        "max_abs_error": max_abs_error,
        "checksum": float(out.sum()) if result.ok else None,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    build_summary = build_package(output_path)
    run_summary = run_package(output_path) if build_summary["ok"] else None
    return {
        "example": "pto_pypto_swiglu",
        "compile": compile_summary,
        "replay": replay_summary,
        "build": build_summary,
        "run": run_summary,
    }


def main() -> None:
    print(json.dumps(run_demo(Path("artifacts") / "pto_pypto_swiglu"), indent=2))


if __name__ == "__main__":
    main()
