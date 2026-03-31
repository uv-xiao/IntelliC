from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.kernel import buffer, kernel, scalar, store
from htp.routine import call, fifo_channel, program
from htp.types import bf16, channel_type, dim, f32, index, shape, tensor


@kernel
def decode_step(
    hidden: buffer(type=tensor(f32, shape(dim("B"), dim("H"))), role="input"),
    weights: buffer(type=tensor(bf16, shape(dim("H"), dim("H"))), role="input"),
    next_hidden: buffer(type=tensor(f32, shape(dim("B"), dim("H"))), role="output"),
    B: scalar(dtype=index, role="shape"),
    H: scalar(dtype=index, role="shape"),
) -> None:
    store(next_hidden, hidden @ weights)


@program(target="nvgpu-ampere")
def serving_routine(
    hidden: buffer(type=tensor(f32, shape(dim("B"), dim("H"))), role="input"),
    weights: buffer(type=tensor(bf16, shape(dim("H"), dim("H"))), role="input"),
    next_hidden: buffer(type=tensor(f32, shape(dim("B"), dim("H"))), role="output"),
    B: scalar(dtype=index, role="shape"),
    H: scalar(dtype=index, role="shape"),
) -> None:
    """Serving routine with explicit serving phases, states, and typed channels."""

    fifo_channel("token_batches", type=channel_type(f32, capacity=2))
    fifo_channel("decoded_batches", type=channel_type(f32, capacity=2))

    prefill = call(
        decode_step,
        hidden,
        weights,
        next_hidden,
        B,
        H,
        task="prefill",
        phase="prefill",
        role="compute",
        state="kv_fill",
        stream="token_batches",
        batch="prompt_tokens",
    )
    decode_step_0 = call(
        decode_step,
        next_hidden,
        weights,
        next_hidden,
        B,
        H,
        task="decode_step_0",
        after=prefill,
        phase="decode",
        role="compute",
        state="token_step_0",
        stream="decoded_batches",
        batch="token_batch",
    )
    decode_step_1 = call(
        decode_step,
        next_hidden,
        weights,
        next_hidden,
        B,
        H,
        task="decode_step_1",
        after=decode_step_0,
        phase="decode",
        role="compute",
        state="token_step_1",
        stream="decoded_batches",
        batch="token_batch",
    )
    sample = call(
        decode_step,
        next_hidden,
        weights,
        next_hidden,
        B,
        H,
        task="sample",
        after=decode_step_1,
        phase="sample",
        role="compute",
        state="token_selection",
        stream="decoded_batches",
        batch="token_batch",
    )
    call(
        decode_step,
        next_hidden,
        weights,
        next_hidden,
        B,
        H,
        task="writeback",
        after=sample,
        phase="writeback",
        role="consumer",
        state="output_commit",
        stream="decoded_batches",
        batch="token_batch",
    )


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-ampere",
        program=serving_routine,
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
    state = json.loads((package_dir / "ir" / "stages" / stage_id / "state.json").read_text())
    return {
        "ok": replay.ok,
        "stage_id": stage_id,
        "entry": replay.entry,
        "diagnostics": replay.diagnostics,
        "workload_ir": state["items"]["workload_ir"],
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
