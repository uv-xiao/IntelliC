"""FlashComm-inspired token-dispatch pipeline on the traced CSP surface.

The example is calibrated against LittleKernel's producer-consumer dispatch
story: stage a tile, route it, commit it, then retire the delivery.
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
def dispatch_token_tile(
    src_tokens: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="input"),
    route_weights: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="input"),
    dst_tokens: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="output"),
    tile_tokens: scalar(dtype="i32", role="shape"),
    hidden: scalar(dtype="i32", role="shape"),
) -> None:
    """One tile movement step in the dispatch pipeline."""

    store(dst_tokens, src_tokens * route_weights)


@csp_program(
    target="nvgpu-ampere",
)
def channel_pipeline(
    token_tile: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="input"),
    stage_weights: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="input"),
    route_weights: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="input"),
    commit_weights: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="input"),
    retire_weights: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="input"),
    staged_tile: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="output"),
    routed_tile: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="output"),
    delivered_tile: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="output"),
    retired_tile: buffer(dtype="f32", shape=("tile_tokens", "hidden"), role="output"),
    tile_tokens: scalar(dtype="i32", role="shape"),
    hidden: scalar(dtype="i32", role="shape"),
) -> None:
    staged_tiles = fifo("staged_tiles", dtype="f32", capacity=2)
    routed_tiles = fifo("routed_tiles", dtype="f32", capacity=2)
    completion_tokens = fifo("completion_tokens", dtype="f32", capacity=1)
    process(
        "stage_hbm_tile",
        kernel=dispatch_token_tile,
        args=(token_tile, stage_weights, staged_tile, tile_tokens, hidden),
        steps=[put(staged_tiles)],
    )
    process(
        "route_peer_tile",
        kernel=dispatch_token_tile,
        args=(staged_tile, route_weights, routed_tile, tile_tokens, hidden),
        steps=[get(staged_tiles), put(routed_tiles)],
    )
    process(
        "commit_remote_tile",
        kernel=dispatch_token_tile,
        args=(routed_tile, commit_weights, delivered_tile, tile_tokens, hidden),
        steps=[get(routed_tiles), put(completion_tokens)],
    )
    process(
        "retire_delivery",
        kernel=dispatch_token_tile,
        args=(delivered_tile, retire_weights, retired_tile, tile_tokens, hidden),
        steps=[get(completion_tokens)],
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
