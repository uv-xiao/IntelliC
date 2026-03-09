from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import RunnablePySpec, StageSpec, write_stage
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult, StageFile
from htp.passes.program_model import (
    build_schedule_plan,
    build_semantic_model,
    build_type_layout_effects,
    canonicalize_program,
    normalize_target,
    scheduled_ops_from_plan,
    stage_payloads_from_program,
)
from htp.runtime import Runtime, extensions

from .export import analyze_program, eligibility_for, export_program, normalize_expr_program
from .import_ import _parse_module, import_program_from_module

EXTENSION_ID = "htp_ext.mlir_cse"
EXTENSION_DIR = Path("extensions") / "mlir_cse"
EXPORT_STAGE_DIR = Path("ir") / "stages" / "s01" / "islands" / "mlir_cse"
IMPORT_STAGE_DIR = Path("ir") / "stages" / "s02" / "islands" / "mlir_cse"
EXPORT_PASS_ID = "htp_ext.mlir_cse::export@1"
IMPORT_PASS_ID = "htp_ext.mlir_cse::import@1"

EXPORT_CONTRACT = PassContract.analysis(
    pass_id=EXPORT_PASS_ID,
    owner=EXTENSION_ID,
    requires=("Semantic.ModelBuilt@1", "Extension.MLIRCSEEligible@1"),
    provides=("Extension.MLIRCSEExported@1",),
    outputs=("island.mlir.input", "island.mlir.pipeline", "island.mlir.ledger"),
)
IMPORT_CONTRACT = PassContract(
    pass_id=IMPORT_PASS_ID,
    owner=EXTENSION_ID,
    kind="transform",
    ast_effect="mutates",
    requires=("Extension.MLIRCSEExported@1",),
    provides=("Extension.MLIRCSEImported@1", "Semantic.ModelBuilt@1"),
    outputs=("ir.ast", "ir.kernel", "ir.workload", "island.mlir.output", "island.mlir.import"),
)


def emit_package(package_dir: Path | str, *, program: Mapping[str, Any]) -> dict[str, Any]:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)

    eligibility = eligibility_for(program)
    if not eligibility["ok"]:
        raise ValueError(f"Program is not eligible for MLIR CSE island: {eligibility['reasons']}")

    normalized_program = normalize_expr_program(program)
    input_mlir, ledger = export_program(normalized_program)
    output_mlir, _transform = _run_mlir_cse_pipeline(input_mlir)
    imported_program, import_summary, entity_map, binding_map = import_program_from_module(
        output_mlir, ledger
    )
    analysis = analyze_program(normalized_program)
    _write_extension_artifacts(
        package_path,
        input_mlir=input_mlir,
        output_mlir=output_mlir,
        eligibility=eligibility,
        ledger=ledger,
        import_summary=import_summary,
        entity_map=entity_map,
        binding_map=binding_map,
    )
    _write_stage_island_artifacts(
        package_path,
        input_mlir=input_mlir,
        output_mlir=output_mlir,
        eligibility=eligibility,
        ledger=ledger,
        import_summary=import_summary,
        entity_map=entity_map,
        binding_map=binding_map,
    )

    export_program_state = _semanticize_expr_program(normalized_program)
    import_program_state = _semanticize_expr_program(imported_program)

    export_payloads = stage_payloads_from_program(export_program_state)
    import_payloads = stage_payloads_from_program(import_program_state)

    stage_export = write_stage(
        package_path,
        StageSpec(
            stage_id="s01",
            pass_id=EXPORT_PASS_ID,
            islands=({"island_id": "mlir_cse", "dir": EXPORT_STAGE_DIR.as_posix()},),
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
                "pass": EXPORT_PASS_ID,
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
            pass_id=IMPORT_PASS_ID,
            islands=({"island_id": "mlir_cse", "dir": IMPORT_STAGE_DIR.as_posix()},),
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
                "pass": IMPORT_PASS_ID,
                "runnable_py": "preserves",
                "modes": ["sim"],
                "extension": EXTENSION_ID,
                "rewrites": import_summary["rewrites"],
            },
            entity_map_payload=entity_map,
            binding_map_payload=binding_map,
        ),
    )
    manifest = write_manifest(package_path, current_stage="s02", stages=[stage_export, stage_import])
    manifest["target"] = {"backend": "ext-demo", "variant": "sim"}
    manifest["extensions"] = {
        "mlir_cse": {
            "input": (EXTENSION_DIR / "input.mlir").as_posix(),
            "output": (EXTENSION_DIR / "output.mlir").as_posix(),
            "pipeline": (EXTENSION_DIR / "pipeline.txt").as_posix(),
            "ledger": (EXTENSION_DIR / "ledger.json").as_posix(),
            "eligibility": (EXTENSION_DIR / "eligibility.json").as_posix(),
            "import_summary": (EXTENSION_DIR / "import_summary.json").as_posix(),
            "entity_map": (EXTENSION_DIR / "entity_map.json").as_posix(),
            "binding_map": (EXTENSION_DIR / "binding_map.json").as_posix(),
        }
    }
    manifest_path = package_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def register_replay_handler(*, runtime: Runtime | None = None) -> None:
    extensions.register(EXTENSION_ID, "replay_cse", _replay_handler, runtime=runtime)


def registered_passes():
    from htp.passes.registry import RegisteredPass

    return (
        RegisteredPass(contract=EXPORT_CONTRACT, run=run_export_pass),
        RegisteredPass(contract=IMPORT_CONTRACT, run=run_import_pass),
    )


def pipeline_templates(*, program: Mapping[str, Any], required_outputs: tuple[str, ...]):
    if not eligibility_for(program)["ok"]:
        return ()
    from htp.pipeline.registry import default_template
    from htp.solver import PipelineTemplate

    base = default_template(target=normalize_target(dict(program)), required_outputs=required_outputs)
    insertion_index = next(
        index
        for index, contract in enumerate(base.passes)
        if contract.pass_id == "htp::typecheck_layout_effects@1"
    )
    passes = list(base.passes)
    passes[insertion_index:insertion_index] = [EXPORT_CONTRACT, IMPORT_CONTRACT]
    return (
        PipelineTemplate(
            template_id="htp.default+htp_ext.mlir_cse.v1",
            passes=tuple(passes),
            required_outputs=required_outputs,
            selection_cost=base.selection_cost + 25,
            extension_steps=(EXTENSION_ID,),
        ),
    )


def extension_solver_result(program: Mapping[str, Any]) -> dict[str, Any]:
    eligibility = eligibility_for(program)
    return {
        "eligible": bool(eligibility["ok"]),
        "provides": ["Extension.MLIRCSEEligible@1"] if eligibility["ok"] else [],
        "pipeline_templates": [
            template.template_id for template in pipeline_templates(program=program, required_outputs=())
        ],
        "reasons": list(eligibility["reasons"]),
        "failed_rules": list(eligibility["failed_rules"]),
        "satisfied_rules": list(eligibility["satisfied_rules"]),
    }


def run_export_pass(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before
    eligibility = eligibility_for(program)
    if not eligibility["ok"]:
        raise ValueError(f"Program is not eligible for MLIR CSE island: {eligibility['reasons']}")
    normalized_program = normalize_expr_program(program)
    input_mlir, ledger = export_program(normalized_program)
    stage_payloads = stage_payloads_from_program(program)
    return dict(program), PassResult(
        runnable_py=RunnablePySpec(status="preserves", modes=("sim",), program_text=_export_stage_program()),
        islands=({"island_id": "mlir_cse", "dir": "islands/mlir_cse"},),
        program_ast_payload=stage_payloads["program_ast_payload"],
        kernel_ir_payload=stage_payloads["kernel_ir_payload"],
        workload_ir_payload=stage_payloads["workload_ir_payload"],
        types_payload=stage_payloads["types_payload"],
        layout_payload=stage_payloads["layout_payload"],
        effects_payload=stage_payloads["effects_payload"],
        schedule_payload=stage_payloads["schedule_payload"],
        entities_payload=stage_payloads["entities_payload"],
        bindings_payload=stage_payloads["bindings_payload"],
        stage_files=(
            StageFile(path="islands/mlir_cse/input.mlir", text=input_mlir),
            StageFile(path="islands/mlir_cse/pipeline.txt", text="canonicalize\ncse\n"),
            StageFile(path="islands/mlir_cse/eligibility.json", payload=dict(eligibility)),
            StageFile(path="islands/mlir_cse/ledger.json", payload=dict(ledger)),
        ),
        summary_payload={"extension": EXTENSION_ID, "pass": EXPORT_PASS_ID, "eligible": True},
        time_ms=0.3,
    )


def run_import_pass(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before
    normalized_program = normalize_expr_program(program)
    input_mlir, ledger = export_program(normalized_program)
    output_mlir, _transform = _run_mlir_cse_pipeline(input_mlir)
    imported_program, import_summary, entity_map, binding_map = import_program_from_module(
        output_mlir, ledger
    )
    next_program = _program_state_from_expr_program(imported_program, template_program=program)
    stage_payloads = stage_payloads_from_program(next_program)
    return next_program, PassResult(
        runnable_py=RunnablePySpec(
            status="preserves",
            modes=("sim",),
            program_text=_import_stage_program(imported_program, import_summary, imported_program["inputs"]),
        ),
        islands=({"island_id": "mlir_cse", "dir": "islands/mlir_cse"},),
        program_ast_payload=stage_payloads["program_ast_payload"],
        kernel_ir_payload=stage_payloads["kernel_ir_payload"],
        workload_ir_payload=stage_payloads["workload_ir_payload"],
        types_payload=stage_payloads["types_payload"],
        layout_payload=stage_payloads["layout_payload"],
        effects_payload=stage_payloads["effects_payload"],
        schedule_payload=stage_payloads["schedule_payload"],
        entities_payload=stage_payloads["entities_payload"],
        bindings_payload=stage_payloads["bindings_payload"],
        stage_files=(
            StageFile(path="islands/mlir_cse/output.mlir", text=output_mlir),
            StageFile(path="islands/mlir_cse/import_summary.json", payload=dict(import_summary)),
        ),
        entity_map_payload=entity_map,
        binding_map_payload=binding_map,
        summary_payload={
            "extension": EXTENSION_ID,
            "pass": IMPORT_PASS_ID,
            "rewrites": import_summary["rewrites"],
        },
        time_ms=0.4,
    )


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
    input_mlir: str,
    output_mlir: str,
    eligibility: Mapping[str, Any],
    ledger: Mapping[str, Any],
    import_summary: Mapping[str, Any],
    entity_map: Mapping[str, Any],
    binding_map: Mapping[str, Any],
) -> None:
    extension_dir = package_path / EXTENSION_DIR
    extension_dir.mkdir(parents=True, exist_ok=True)
    (extension_dir / "input.mlir").write_text(input_mlir)
    (extension_dir / "output.mlir").write_text(output_mlir)
    (extension_dir / "pipeline.txt").write_text("canonicalize\ncse\n")
    (extension_dir / "eligibility.json").write_text(json.dumps(dict(eligibility), indent=2) + "\n")
    (extension_dir / "ledger.json").write_text(json.dumps(dict(ledger), indent=2) + "\n")
    (extension_dir / "import_summary.json").write_text(json.dumps(dict(import_summary), indent=2) + "\n")
    (extension_dir / "entity_map.json").write_text(json.dumps(dict(entity_map), indent=2) + "\n")
    (extension_dir / "binding_map.json").write_text(json.dumps(dict(binding_map), indent=2) + "\n")


def _write_stage_island_artifacts(
    package_path: Path,
    *,
    input_mlir: str,
    output_mlir: str,
    eligibility: Mapping[str, Any],
    ledger: Mapping[str, Any],
    import_summary: Mapping[str, Any],
    entity_map: Mapping[str, Any],
    binding_map: Mapping[str, Any],
) -> None:
    export_dir = package_path / EXPORT_STAGE_DIR
    import_dir = package_path / IMPORT_STAGE_DIR
    export_dir.mkdir(parents=True, exist_ok=True)
    import_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "input.mlir").write_text(input_mlir)
    (export_dir / "pipeline.txt").write_text("canonicalize\ncse\n")
    (export_dir / "eligibility.json").write_text(json.dumps(dict(eligibility), indent=2) + "\n")
    (export_dir / "ledger.json").write_text(json.dumps(dict(ledger), indent=2) + "\n")
    (import_dir / "output.mlir").write_text(output_mlir)
    (import_dir / "import_summary.json").write_text(json.dumps(dict(import_summary), indent=2) + "\n")
    (import_dir / "entity_map.json").write_text(json.dumps(dict(entity_map), indent=2) + "\n")
    (import_dir / "binding_map.json").write_text(json.dumps(dict(binding_map), indent=2) + "\n")


def _run_mlir_cse_pipeline(module_text: str) -> tuple[str, dict[str, Any]]:
    parsed = _parse_module(module_text)
    aliases: dict[str, str] = {}
    seen: dict[tuple[str, str, str], str] = {}
    kept_ops: list[dict[str, str]] = []
    for op in parsed["ops"]:
        lhs = aliases.get(op["lhs"], op["lhs"])
        rhs = aliases.get(op["rhs"], op["rhs"])
        signature = (op["op"], lhs, rhs)
        existing = seen.get(signature)
        if existing is not None:
            aliases[op["result"]] = existing
            continue
        kept_ops.append({**op, "lhs": lhs, "rhs": rhs})
        seen[signature] = op["result"]
    return_value = aliases.get(parsed["return"], parsed["return"])
    return _render_mlir_module(parsed["entry"], parsed["args"], kept_ops, return_value), {"aliases": aliases}


def _render_mlir_module(
    entry: str, args: tuple[str, ...], ops: list[dict[str, str]], return_value: str
) -> str:
    arguments = ", ".join(f"%{name}: i32" for name in args)
    lines = ["module {", f"  func.func @{entry}({arguments}) -> i32 {{"]
    for op in ops:
        op_name = "arith.addi" if op["op"] == "add" else "arith.muli"
        lines.append(f"    {op['result']} = {op_name} {op['lhs']}, {op['rhs']} : i32")
    lines.append(f"    return {return_value} : i32")
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines) + "\n"


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


def _program_state_from_expr_program(
    expr_program: Mapping[str, Any], *, template_program: Mapping[str, Any]
) -> dict[str, Any]:
    original_kernel = template_program.get("kernel", {})
    original_arg_map = {
        str(argument["name"]): dict(argument)
        for argument in original_kernel.get("args", ())
        if isinstance(argument, Mapping) and isinstance(argument.get("name"), str)
    }
    inputs = tuple(str(name) for name in expr_program.get("inputs", ()))
    kernel = {
        "name": str(expr_program["entry"]),
        "args": [
            {
                "name": name,
                "kind": str(original_arg_map.get(name, {}).get("kind", "scalar")),
                "dtype": str(original_arg_map.get(name, {}).get("dtype", "i32")),
                "shape": list(original_arg_map.get(name, {}).get("shape", ())),
                "role": str(original_arg_map.get(name, {}).get("role", "input")),
            }
            for name in inputs
        ],
        "ops": [
            {
                "op": "elementwise_binary",
                "operator": str(expr["op"]),
                "lhs": str(expr["lhs"]),
                "rhs": str(expr["rhs"]),
                "out": str(expr["target"]),
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
                "args": list(inputs),
            }
        ],
        "channels": [],
        "dependencies": [],
    }
    state = dict(template_program)
    state.update(
        {
            "entry": str(expr_program["entry"]),
            "kernel": kernel,
            "workload": workload,
            "analysis": dict(template_program.get("analysis", {})),
            "package": dict(template_program.get("package", {"emitted": False})),
        }
    )
    state["canonical_ast"] = canonicalize_program(state)
    kernel_ir, workload_ir, entities_payload, bindings_payload = build_semantic_model(state["canonical_ast"])
    state["kernel_ir"] = kernel_ir
    state["workload_ir"] = workload_ir
    state["entities_payload"] = entities_payload
    state["bindings_payload"] = bindings_payload
    state.pop("types", None)
    state.pop("layout", None)
    state.pop("effects", None)
    state.pop("schedule", None)
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


__all__ = [
    "EXTENSION_DIR",
    "EXTENSION_ID",
    "EXPORT_CONTRACT",
    "EXPORT_PASS_ID",
    "IMPORT_CONTRACT",
    "IMPORT_PASS_ID",
    "emit_package",
    "extension_solver_result",
    "pipeline_templates",
    "register_replay_handler",
    "registered_passes",
    "run_export_pass",
    "run_import_pass",
]
