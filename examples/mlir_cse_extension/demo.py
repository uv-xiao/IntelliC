from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind
from htp.solver import solve_default_pipeline
from htp_ext.mlir_cse import emit_package
from htp_ext.mlir_cse.island import register_replay_handler


def build_demo_program() -> dict[str, object]:
    return {
        "entry": "expr_demo",
        "target": {"backend": "nvgpu", "option": "ampere"},
        "exprs": [
            {"target": "sum0", "op": "add", "lhs": "x", "rhs": "y"},
            {"target": "delta0", "op": "sub", "lhs": "x", "rhs": "y"},
            {"target": "out", "op": "mul", "lhs": "sum0", "rhs": "delta0"},
        ],
        "result": "out",
        "extensions": {"requested": ["htp_ext.mlir_cse"]},
    }


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    program = build_demo_program()
    solver_result = solve_default_pipeline(program=program)
    manifest = emit_package(output_path, program=program)
    return {
        "package_dir": output_path.as_posix(),
        "solver": {
            "ok": solver_result.ok,
            "template_id": solver_result.template_id,
            "extension_results": solver_result.extension_results,
        },
        "manifest_path": (output_path / "manifest.json").as_posix(),
        "manifest_target": dict(manifest["target"]),
    }


def replay_latest_stage(output_dir: Path | str) -> dict[str, Any]:
    package_dir = Path(output_dir)
    register_replay_handler()
    session = bind(package_dir).load(mode="sim")
    stage_id = session.manifest["stages"]["current"]
    replay = session.replay(stage_id, trace="basic", kwargs={"x": 7, "y": 4, "out": 0})
    manifest = json.loads((package_dir / "manifest.json").read_text())
    return {
        "ok": replay.ok,
        "stage_id": stage_id,
        "entry": replay.entry,
        "diagnostics": replay.diagnostics,
        "result": replay.result,
        "extensions": manifest.get("extensions", {}),
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    return {
        "example": "mlir_cse_extension",
        "compile": compile_example(output_path),
        "replay": replay_latest_stage(output_path),
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "mlir_cse_extension")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
