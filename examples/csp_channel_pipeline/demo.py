from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.csp import program as csp_program
from htp.kernel import (
    barrier,
    broadcast,
    buffer,
    channel_recv,
    channel_send,
    kernel,
    reduction_sum,
    scalar,
    store,
)


@kernel
def channel_stage(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    """Streaming tile stage with explicit channel protocol effects."""

    tile_payload = channel_recv("tiles", dtype="f32", shape=("M", "N"))
    tile_summary = reduction_sum(tile_payload, axis=0, dtype="f32", shape=("N",))
    channel_send(tile_summary, channel="partials")
    merged_summary = channel_recv("partials", dtype="f32", shape=("N",))
    expanded_summary = broadcast(merged_summary, shape=("M", "N"), dtype="f32")
    barrier()
    store(C, expanded_summary)


@csp_program(target="nvgpu-ampere", kernel=channel_stage)
def token_pipeline(p) -> None:
    tiles = p.fifo("tiles", dtype="f32", capacity=2)
    partials = p.fifo("partials", dtype="f32", capacity=1)
    ready_rows = p.fifo("ready_rows", dtype="f32", capacity=1)

    dispatch = p.process("dispatch_tiles", task_id="dispatch_tiles").role("producer")
    dispatch.compute_step("pack_tile", source=p.args.A)
    dispatch.put(tiles)

    combine = p.process("combine_tiles", task_id="combine_tiles").role("router")
    combine.get(tiles)
    combine.compute_step("reduce_partials", channel=tiles)
    combine.put(partials)

    finalize = p.process("finalize_rows", task_id="finalize_rows").role("reducer")
    finalize.get(partials)
    finalize.compute_step("normalize_rows", channel=partials)
    finalize.put(ready_rows)

    writeback = p.process("writeback_tiles", task_id="writeback_tiles").role("consumer")
    writeback.get(ready_rows)
    writeback.compute_step("write_output", target=p.args.C)


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=token_pipeline,
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
    state = json.loads((package_dir / "ir" / "stages" / stage_id / "state.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "effects": state["aspects"]["effects"],
        "workload_ir": state["items"]["workload_ir"],
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
