from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.passes.program_model import (
    build_schedule_plan,
    build_semantic_model,
    build_type_layout_effects,
    canonicalize_program,
    scheduled_ops_from_plan,
    stage_payloads_from_program,
)
from htp.runtime import Runtime, extensions

from .export import analyze_program, eligibility_for, export_program, normalize_expr_program
from .import_ import import_program

EXTENSION_ID = "htp_ext.mlir_cse"
EXTENSION_DIR = Path("extensions") / "mlir_cse"
EXPORT_STAGE_DIR = Path("ir") / "stages" / "s01" / "islands" / "mlir_cse"
IMPORT_STAGE_DIR = Path("ir") / "stages" / "s02" / "islands" / "mlir_cse"


def emit_package(package_dir: Path | str, *, program: Mapping[str, Any]) -> dict[str, Any]:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)

    eligibility = eligibility_for(program)
    if not eligibility["ok"]:
        raise ValueError(f"Program is not eligible for MLIR CSE island: {eligibility['reasons']}")

    normalized_program = normalize_expr_program(program)
    module_text, ledger = export_program(normalized_program)
    imported_program, import_summary = import_program(normalized_program)
    analysis = analyze_program(normalized_program)
    _write_extension_artifacts(
        package_path,
        module_text=module_text,
        eligibility=eligibility,
        ledger=ledger,
        import_summary=import_summary,
    )
    _write_stage_island_artifacts(
        package_path,
        module_text=module_text,
        eligibility=eligibility,
        ledger=ledger,
        import_summary=import_summary,
    )

    export_program_state = _semanticize_expr_program(normalized_program)
    import_program_state = _semanticize_expr_program(imported_program)

    export_payloads = stage_payloads_from_program(export_program_state)
    import_payloads = stage_payloads_from_program(import_program_state)

    stage_export = write_stage(
        package_path,
        StageSpec(
            stage_id="s01",
            pass_id="htp_ext.mlir_cse::export@1",
            islands=(({"island_id": "mlir_cse", "dir": EXPORT_STAGE_DIR.as_posix()}),),
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text=_export_stage_program(),
            ),
            program_ast_payload=export_payloads["program_ast_payload"],
            kernel_ir_payload=export_payloads["kernel_ir_payload"],
            workload_ir_payload=export_payloads["workload_ir_payload"],
            types_payload=export_payloads["types_payload"],
            layout_payload=export_payloads["layout_payload"],
            effects_payload=export_payloads["effects_payload"],
            schedule_payload=export_payloads["schedule_payload"],
            entities_payload=export_payloads["entities_payload"],
            bindings_payload=export_payloads["bindings_payload"],
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
            islands=(({"island_id": "mlir_cse", "dir": IMPORT_STAGE_DIR.as_posix()}),),
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text=_import_stage_program(imported_program, import_summary, analysis["inputs"]),
            ),
            program_ast_payload=import_payloads["program_ast_payload"],
            kernel_ir_payload=import_payloads["kernel_ir_payload"],
            workload_ir_payload=import_payloads["workload_ir_payload"],
            types_payload=import_payloads["types_payload"],
            layout_payload=import_payloads["layout_payload"],
            effects_payload=import_payloads["effects_payload"],
            schedule_payload=import_payloads["schedule_payload"],
            entities_payload=import_payloads["entities_payload"],
            bindings_payload=import_payloads["bindings_payload"],
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


def _write_stage_island_artifacts(
    package_path: Path,
    *,
    module_text: str,
    eligibility: Mapping[str, Any],
    ledger: Mapping[str, Any],
    import_summary: Mapping[str, Any],
) -> None:
    export_dir = package_path / EXPORT_STAGE_DIR
    import_dir = package_path / IMPORT_STAGE_DIR
    export_dir.mkdir(parents=True, exist_ok=True)
    import_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "module.mlir").write_text(module_text)
    (export_dir / "eligibility.json").write_text(json.dumps(dict(eligibility), indent=2) + "\n")
    (export_dir / "ledger.json").write_text(json.dumps(dict(ledger), indent=2) + "\n")
    (import_dir / "import_summary.json").write_text(json.dumps(dict(import_summary), indent=2) + "\n")


def _semanticize_expr_program(expr_program: Mapping[str, Any]) -> dict[str, Any]:
    analysis = analyze_program(expr_program)
    kernel = {
        "name": str(expr_program["entry"]),
        "args": [
            {"name": name, "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"}
            for name in analysis["inputs"]
        ],
        "ops": [
            {
                "op": "elementwise_binary",
                "operator": expr["op"],
                "lhs": expr["lhs"],
                "rhs": expr["rhs"],
                "out": expr["target"],
                "shape": [],
                "dtype": "i32",
            }
            for expr in expr_program["exprs"]
        ],
    }
    workload = {
        "entry": str(expr_program["entry"]),
        "tasks": [
            {
                "task_id": "task0",
                "kind": "kernel_call",
                "kernel": str(expr_program["entry"]),
                "args": list(analysis["inputs"]),
            }
        ],
        "channels": [],
        "dependencies": [],
    }
    state = {
        "entry": str(expr_program["entry"]),
        "kernel": kernel,
        "workload": workload,
        "analysis": {},
        "package": {"emitted": False},
        "target": {"backend": "ext-demo", "option": "sim"},
    }
    state["canonical_ast"] = canonicalize_program(state)
    kernel_ir, workload_ir, entities_payload, bindings_payload = build_semantic_model(state["canonical_ast"])
    state["kernel_ir"] = kernel_ir
    state["workload_ir"] = workload_ir
    state["entities_payload"] = entities_payload
    state["bindings_payload"] = bindings_payload
    types, layout, effects = build_type_layout_effects(
        kernel_ir, workload_ir, target={"backend": "ext-demo", "option": "sim"}
    )
    state["types"] = types
    state["layout"] = layout
    state["effects"] = effects
    schedule_plan = build_schedule_plan(
        entry=state["entry"],
        kernel_ir=kernel_ir,
        effects=effects,
        target={"backend": "ext-demo", "option": "sim"},
    )
    state["analysis"]["schedule"] = schedule_plan
    state["schedule"] = {
        "schema": "htp.schedule.v1",
        "applied": True,
        "ticks": list(schedule_plan["ticks"]),
        "pipeline_depth": schedule_plan["pipeline_depth"],
        "ordered_ops": [item["op_id"] for item in scheduled_ops_from_plan(schedule_plan)],
    }
    return state


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


def _import_stage_program(
    program: Mapping[str, Any], summary: Mapping[str, Any], inputs: tuple[str, ...]
) -> str:
    return "\n".join(
        (
            "from htp.runtime import default_runtime, extensions",
            "",
            'STAGE_ID = "s02"',
            "",
            "PROGRAM = " + repr(dict(program)),
            "SUMMARY = " + repr(dict(summary)),
            "INPUTS = " + repr(inputs),
            "",
            'def run(*, runtime=None, mode="sim", trace=None, **kwargs):',
            "    resolved_runtime = default_runtime() if runtime is None else runtime",
            "    values = {name: kwargs[name] for name in INPUTS}",
            "    return extensions.invoke(",
            f"        {EXTENSION_ID!r},",
            '        "replay_cse",',
            "        payload={",
            '            "program": PROGRAM,',
            '            "summary": SUMMARY,',
            '            "values": values,',
            "        },",
            "        mode=mode,",
            "        trace=trace,",
            "        runtime=resolved_runtime,",
            "    )",
            "",
        )
    )


__all__ = ["EXTENSION_DIR", "EXTENSION_ID", "emit_package", "register_replay_handler"]
