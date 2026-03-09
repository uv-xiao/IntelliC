"""Affine streaming pipeline example on the traced CSP surface.

The program models a small neural-network-style pipeline where named processes
exchange typed tile streams instead of assembling a raw CSP payload.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.csp import fifo, get, process, put
from htp.csp import program as csp_program
from htp.kernel import buffer, kernel, scalar, store


@kernel
def affine_stage(
    src: buffer(dtype="f32", shape=("size",), role="input"),
    scale: buffer(dtype="f32", shape=("size",), role="input"),
    bias: buffer(dtype="f32", shape=("size",), role="input"),
    dst: buffer(dtype="f32", shape=("size",), role="output"),
    size: scalar(dtype="i32", role="shape"),
) -> None:
    """One affine transform stage in the streamed pipeline."""

    store(dst, src * scale + bias)


@csp_program(
    target="nvgpu-ampere",
)
def channel_pipeline(
    activations: buffer(dtype="f32", shape=("size",), role="input"),
    norm_scale: buffer(dtype="f32", shape=("size",), role="input"),
    norm_bias: buffer(dtype="f32", shape=("size",), role="input"),
    proj_scale: buffer(dtype="f32", shape=("size",), role="input"),
    proj_bias: buffer(dtype="f32", shape=("size",), role="input"),
    out_scale: buffer(dtype="f32", shape=("size",), role="input"),
    out_bias: buffer(dtype="f32", shape=("size",), role="input"),
    hidden: buffer(dtype="f32", shape=("size",), role="output"),
    projected: buffer(dtype="f32", shape=("size",), role="output"),
    output: buffer(dtype="f32", shape=("size",), role="output"),
    size: scalar(dtype="i32", role="shape"),
) -> None:
    input_tiles = fifo("input_tiles", dtype="f32", capacity=2)
    hidden_tiles = fifo("hidden_tiles", dtype="f32", capacity=1)
    completions = fifo("completions", dtype="f32", capacity=1)
    process(
        "load_norm",
        kernel=affine_stage,
        args=(activations, norm_scale, norm_bias, hidden, size),
        steps=[put(input_tiles), put(hidden_tiles)],
    )
    process(
        "project",
        kernel=affine_stage,
        args=(hidden, proj_scale, proj_bias, projected, size),
        steps=[get(input_tiles), get(hidden_tiles), put(completions)],
    )
    process(
        "writeback",
        kernel=affine_stage,
        args=(projected, out_scale, out_bias, output, size),
        steps=[get(completions)],
    )


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=channel_pipeline,
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
    workload_ir = json.loads((package_dir / "ir" / "stages" / stage_id / "workload_ir.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "effects": effects,
        "workload_ir": workload_ir,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    return {
        "example": "patterns.csp.channel_pipeline",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "patterns" / "csp" / "channel_pipeline")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
