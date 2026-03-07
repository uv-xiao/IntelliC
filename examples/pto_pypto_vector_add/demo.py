from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import bind, compile_program


PYPT0_VECTOR_ADD_PROGRAM: dict[str, Any] = {
    "entry": "vector_add",
    "ops": ["load_tile", "compute_tile", "store_tile"],
}


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    """Compile a PyPTO-style vector-add kernel to the PTO backend.

    The example mirrors the shape of the `host_build_graph/vector_example`
    references: a simple tile kernel, a PTO package, and the standard
    `kernel_config.py` / orchestration contract.
    """

    package = compile_program(
        package_dir=Path(output_dir),
        target="pto-a2a3sim",
        program=dict(PYPT0_VECTOR_ADD_PROGRAM),
    )
    return {
        "package_dir": package.package_dir.as_posix(),
        "target": {
            "backend": package.target.backend,
            "option": package.target.option,
        },
        "manifest_path": (package.package_dir / "manifest.json").as_posix(),
    }


def replay_latest_stage(output_dir: Path | str) -> dict[str, Any]:
    """Replay the latest Python stage.

    Replay is the stable part of the example: it always works in `sim`
    because stages remain runnable Python programs.
    """

    package_dir = Path(output_dir)
    session = bind(package_dir).load(mode="sim")
    # Replaying the latest stage exercises the canonical HTP invariant:
    # the intermediate program is always runnable Python in `sim`.
    stage_id = session.manifest["stages"]["current"]
    result = session.replay(stage_id, trace="basic")
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
    }


def build_package(output_dir: Path | str) -> dict[str, Any]:
    """Materialize PTO runtime binaries through the binding adapter."""

    result = bind(Path(output_dir)).build(mode="sim")
    return {
        "ok": result.ok,
        "mode": result.mode,
        "built_outputs": list(result.built_outputs),
        "diagnostics": list(result.diagnostics),
    }


def run_package(output_dir: Path | str) -> dict[str, Any]:
    """Attempt package execution through `pto-runtime`.

    This step is environment-dependent because the local machine must
    provide the PTO runtime reference checkout and compatible host
    compilation tools.
    """

    result = bind(Path(output_dir)).load(mode="sim").run("vector_add")
    return {
        "ok": result.ok,
        "entry": result.entry,
        "result": result.result,
        "diagnostics": list(result.diagnostics),
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    """Run the full PTO example workflow and return a JSON-friendly summary."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    # Keep the workflow linear and explicit so the example doubles as an
    # executable spec for the intended user-facing API.
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    build_summary = build_package(output_path)
    run_summary = run_package(output_path) if build_summary["ok"] else None
    return {
        "example": "pto_pypto_vector_add",
        "compile": compile_summary,
        "replay": replay_summary,
        "build": build_summary,
        "run": run_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "pto_pypto_vector_add")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
