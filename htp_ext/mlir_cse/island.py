from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.runtime import Runtime, extensions

from .export import eligibility_for, export_program
from .import_ import import_program

EXTENSION_ID = "htp_ext.mlir_cse"
EXTENSION_DIR = Path("extensions") / "mlir_cse"


def emit_package(package_dir: Path | str, *, program: Mapping[str, Any]) -> dict[str, Any]:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)

    eligibility = eligibility_for(program)
    if not eligibility["ok"]:
        raise ValueError(f"Program is not eligible for MLIR CSE island: {eligibility['reasons']}")

    module_text, ledger = export_program(program)
    imported_program, import_summary = import_program(program)
    _write_extension_artifacts(
        package_path,
        module_text=module_text,
        eligibility=eligibility,
        ledger=ledger,
        import_summary=import_summary,
    )

    stage_export = write_stage(
        package_path,
        StageSpec(
            stage_id="s01",
            pass_id="htp_ext.mlir_cse::export@1",
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text=_export_stage_program(),
            ),
            summary_payload={
                "stage_id": "s01",
                "pass": "htp_ext.mlir_cse::export@1",
                "runnable_py": "preserves",
                "modes": ["sim"],
                "extension": EXTENSION_ID,
            },
        ),
    )
    stage_import = write_stage(
        package_path,
        StageSpec(
            stage_id="s02",
            pass_id="htp_ext.mlir_cse::import@1",
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text=_import_stage_program(imported_program, import_summary),
            ),
            summary_payload={
                "stage_id": "s02",
                "pass": "htp_ext.mlir_cse::import@1",
                "runnable_py": "preserves",
                "modes": ["sim"],
                "extension": EXTENSION_ID,
                "rewrites": import_summary["rewrites"],
            },
        ),
    )
    manifest = write_manifest(package_path, current_stage="s02", stages=[stage_export, stage_import])
    manifest["target"] = {"backend": "ext-demo", "variant": "sim"}
    manifest["extensions"] = {
        "mlir_cse": {
            "module": (EXTENSION_DIR / "module.mlir").as_posix(),
            "ledger": (EXTENSION_DIR / "ledger.json").as_posix(),
            "eligibility": (EXTENSION_DIR / "eligibility.json").as_posix(),
            "import_summary": (EXTENSION_DIR / "import_summary.json").as_posix(),
        }
    }
    manifest_path = package_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def register_replay_handler(*, runtime: Runtime | None = None) -> None:
    extensions.register(EXTENSION_ID, "replay_cse", _replay_handler, runtime=runtime)


def _replay_handler(*, payload: Mapping[str, object], mode: str, trace: object | None = None) -> object:
    del mode, trace
    program = payload["program"]
    values = payload["values"]
    summary = payload["summary"]
    env = dict(values)
    for expr in program["exprs"]:
        lhs = env[expr["lhs"]]
        rhs = env[expr["rhs"]]
        env[expr["target"]] = lhs + rhs if expr["op"] == "add" else lhs * rhs
    return {
        "result": env[program["result"]],
        "rewrites": summary["rewrites"],
        "entry": program["entry"],
    }


def _write_extension_artifacts(
    package_path: Path,
    *,
    module_text: str,
    eligibility: Mapping[str, Any],
    ledger: Mapping[str, Any],
    import_summary: Mapping[str, Any],
) -> None:
    extension_dir = package_path / EXTENSION_DIR
    extension_dir.mkdir(parents=True, exist_ok=True)
    (extension_dir / "module.mlir").write_text(module_text)
    (extension_dir / "eligibility.json").write_text(json.dumps(dict(eligibility), indent=2) + "\n")
    (extension_dir / "ledger.json").write_text(json.dumps(dict(ledger), indent=2) + "\n")
    (extension_dir / "import_summary.json").write_text(json.dumps(dict(import_summary), indent=2) + "\n")


def _export_stage_program() -> str:
    return "\n".join(
        (
            'STAGE_ID = "s01"',
            "",
            "def run(*args, **kwargs):",
            '    return {"stage": "s01", "status": "exported"}',
            "",
        )
    )


def _import_stage_program(program: Mapping[str, Any], summary: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            "from htp.runtime import default_runtime, extensions",
            "",
            'STAGE_ID = "s02"',
            "",
            'PROGRAM = ' + repr(dict(program)),
            'SUMMARY = ' + repr(dict(summary)),
            "",
            "def run(*, x, y, z, runtime=None, mode=\"sim\", trace=None):",
            "    resolved_runtime = default_runtime() if runtime is None else runtime",
            f"    return extensions.invoke(",
            f"        {EXTENSION_ID!r},",
            "        \"replay_cse\",",
            "        payload={",
            "            \"program\": PROGRAM,",
            "            \"summary\": SUMMARY,",
            "            \"values\": {\"x\": x, \"y\": y, \"z\": z},",
            "        },",
            "        mode=mode,",
            "        trace=trace,",
            "        runtime=resolved_runtime,",
            "    )",
            "",
        )
    )


__all__ = ["EXTENSION_DIR", "EXTENSION_ID", "emit_package", "register_replay_handler"]
