from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program
from htp.csp import channel, process
from htp.csp import program as csp_program

AIE_CHANNEL_PROGRAM: dict[str, Any] = csp_program(
    entry="aie_pipeline_demo",
    target={"backend": "aie", "option": "xdna2-npu1"},
    kernel={
        "name": "stream_add",
        "args": [
            {"name": "tile_in", "kind": "buffer", "dtype": "i32", "shape": ["size"], "role": "input"},
            {"name": "tile_out", "kind": "buffer", "dtype": "i32", "shape": ["size"], "role": "output"},
            {"name": "size", "kind": "scalar", "dtype": "i32", "shape": [], "role": "shape"},
        ],
        "ops": [
            {
                "op": "elementwise_binary",
                "operator": "add",
                "lhs": "tile_in",
                "rhs": "tile_in",
                "out": "tile_out",
                "shape": ["size"],
                "dtype": "i32",
            }
        ],
    },
    channels=[channel("tiles", dtype="i32", capacity=2)],
    processes=[
        process("producer", task_id="p0", kernel="stream_add", puts=[{"channel": "tiles", "count": 1}]),
        process("consumer", task_id="p1", kernel="stream_add", gets=[{"channel": "tiles", "count": 1}]),
    ],
)


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="aie-xdna2-npu1",
        program=dict(AIE_CHANNEL_PROGRAM),
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
    analysis_index = json.loads(
        (package_dir / "ir" / "stages" / stage_id / "analysis" / "index.json").read_text()
    )
    mapping = json.loads((package_dir / "codegen" / "aie" / "mapping.json").read_text())
    fifos = json.loads((package_dir / "codegen" / "aie" / "fifos.json").read_text())
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "analysis_index": analysis_index,
        "mapping": mapping,
        "fifos": fifos,
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    return {
        "example": "aie_channel_pipeline",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "aie_channel_pipeline")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
