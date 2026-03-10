from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from htp.artifacts.manifest import write_manifest
from htp.artifacts.stages import AnalysisSpec, RunnablePySpec, StageSpec, write_stage
from htp.passes.program_model import (
    build_schedule_plan,
    build_semantic_model,
    build_type_layout_effects,
    canonicalize_program,
    scheduled_ops_from_plan,
    stage_payloads_from_program,
)
from htp.passes.replay_program import render_program_state_module
from htp_ext.aie.declarations import AIE_PROJECT_DIR, declaration_for
from htp_ext.aie.plan import (
    FIFO_PLAN_SCHEMA_ID,
    MAPPING_PLAN_SCHEMA_ID,
    build_fifo_plan,
    build_mapping_plan,
)
from htp_ext.aie.toolchain import AIE_BUILD_PRODUCT_SCHEMA_ID, AIE_HOST_RUNTIME_SCHEMA_ID

AIE_CODEGEN_SCHEMA_ID = "htp.aie.codegen.v1"
AIE_TOOLCHAIN_SCHEMA_ID = "htp.aie.toolchain.v1"


def emit_package(
    package_dir: Path | str,
    *,
    program: Mapping[str, Any],
    profile: str = "xdna2-npu1",
) -> dict[str, Any]:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)

    state = _semanticize_program(program, profile=profile)
    _write_codegen_tree(package_path, state=state, profile=profile)
    manifest = _load_or_seed_manifest(package_path, state)
    manifest["target"] = {
        "backend": "aie",
        "variant": "mlir-aie",
        "hardware_profile": f"amd-xdna2:{profile}",
    }
    manifest["outputs"] = declaration_for(profile).artifact_contract.as_manifest_outputs()
    manifest["extensions"] = {
        "aie": {
            "toolchain_contract": "mlir-aie:dev",
            "mlir": (AIE_PROJECT_DIR / "aie.mlir").as_posix(),
            "toolchain_manifest": declaration_for(profile).artifact_contract.output_path(
                "toolchain_manifest"
            ),
            "sidecars": {
                "mapping": (AIE_PROJECT_DIR / "mapping.json").as_posix(),
                "fifos": (AIE_PROJECT_DIR / "fifos.json").as_posix(),
                "host": (AIE_PROJECT_DIR / "host.py").as_posix(),
            },
            "runtime_contract": "mlir-aie:host-python",
        }
    }
    manifest_path = package_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _load_or_seed_manifest(package_path: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    manifest_path = package_path / "manifest.json"
    stage_id = "s01"
    existing_stages: list[dict[str, Any]] = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if isinstance(manifest.get("stages"), Mapping):
            existing_stages = [
                dict(stage) for stage in manifest["stages"].get("graph", ()) if isinstance(stage, Mapping)
            ]
            stage_id = f"s{len(existing_stages):02d}"
    payloads = stage_payloads_from_program(state)
    stage = write_stage(
        package_path,
        StageSpec(
            stage_id=stage_id,
            pass_id="htp_ext.aie::emit@1",
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text=render_program_state_module(state),
            ),
            analyses=(
                AnalysisSpec(
                    analysis_id="htp_ext.aie::MappingPlan@1",
                    schema=MAPPING_PLAN_SCHEMA_ID,
                    filename="aie_mapping_plan.json",
                    payload=dict(state["analysis"]["aie_mapping"]),
                ),
                AnalysisSpec(
                    analysis_id="htp_ext.aie::FIFOPlan@1",
                    schema=FIFO_PLAN_SCHEMA_ID,
                    filename="aie_fifo_plan.json",
                    payload=dict(state["analysis"]["aie_fifo"]),
                ),
            ),
            program_ast_payload=payloads["program_ast_payload"],
            kernel_ir_payload=payloads["kernel_ir_payload"],
            workload_ir_payload=payloads["workload_ir_payload"],
            types_payload=payloads["types_payload"],
            layout_payload=payloads["layout_payload"],
            effects_payload=payloads["effects_payload"],
            schedule_payload=payloads["schedule_payload"],
            entities_payload=payloads["entities_payload"],
            bindings_payload=payloads["bindings_payload"],
        ),
    )
    return write_manifest(package_path, current_stage=stage_id, stages=[*existing_stages, stage])


def _semanticize_program(program: Mapping[str, Any], *, profile: str) -> dict[str, Any]:
    state = dict(program)
    state["target"] = {"backend": "aie", "option": profile}
    state["analysis"] = dict(state.get("analysis", {}))
    state["package"] = {"emitted": True, "backend": "aie", "entry": str(program["entry"])}
    state["canonical_ast"] = canonicalize_program(state)
    kernel_ir, workload_ir, entities_payload, bindings_payload = build_semantic_model(state["canonical_ast"])
    state["kernel_ir"] = kernel_ir
    state["workload_ir"] = workload_ir
    state["entities_payload"] = entities_payload
    state["bindings_payload"] = bindings_payload
    types, layout, effects = build_type_layout_effects(
        kernel_ir, workload_ir, target={"backend": "aie", "option": profile}
    )
    state["types"] = types
    state["layout"] = layout
    state["effects"] = effects
    schedule_plan = build_schedule_plan(
        entry=str(program["entry"]),
        kernel_ir=kernel_ir,
        effects=effects,
        target={"backend": "aie", "option": profile},
    )
    state["analysis"]["schedule"] = schedule_plan
    state["analysis"]["aie_mapping"] = build_mapping_plan(state, profile=profile)
    state["analysis"]["aie_fifo"] = build_fifo_plan(state)
    state["schedule"] = {
        "schema": "htp.schedule.v1",
        "applied": True,
        "ticks": list(schedule_plan["ticks"]),
        "pipeline_depth": schedule_plan["pipeline_depth"],
        "ordered_ops": [item["op_id"] for item in scheduled_ops_from_plan(schedule_plan)],
    }
    return state


def _write_codegen_tree(package_dir: Path, *, state: Mapping[str, Any], profile: str) -> None:
    codegen_dir = package_dir / AIE_PROJECT_DIR
    codegen_dir.mkdir(parents=True, exist_ok=True)

    mapping = dict(state["analysis"]["aie_mapping"])
    mapping["schema"] = "htp.aie.mapping.v1"
    fifos = dict(state["analysis"]["aie_fifo"])
    fifos["schema"] = "htp.aie.fifos.v1"
    host = "\n".join(
        (
            "from __future__ import annotations",
            "",
            "import json",
            "from pathlib import Path",
            "",
            f"ENTRY = {state['entry']!r}",
            "",
            "def launch(*args, package_dir, build_dir, entry, mode='sim', **kwargs):",
            "    del args, kwargs",
            "    if entry != ENTRY:",
            "        raise ValueError(f'unknown AIE entrypoint: {entry!r}')",
            "    build_path = Path(build_dir) / 'host_runtime.json'",
            "    runtime = None",
            "    if build_path.exists():",
            "        runtime = json.loads(build_path.read_text())",
            "    elif mode == 'device':",
            "        raise ValueError('missing build/aie/host_runtime.json for device launch')",
            "    return {",
            "        'status': 'ok',",
            "        'entry': ENTRY,",
            "        'mode': mode,",
            "        'package_dir': package_dir,",
            f"        'mapping_plan': {mapping['tiles']!r},",
            f"        'fifo_plan': {fifos['channels']!r},",
            "        'runtime': runtime,",
            "    }",
            "",
            "",
        )
    )
    mlir_lines = _render_aie_mlir(state=state, mapping=mapping, fifos=fifos, profile=profile)
    codegen_index = {
        "schema": AIE_CODEGEN_SCHEMA_ID,
        "entry": state["entry"],
        "variant": "mlir-aie",
        "hardware_profile": f"amd-xdna2:{profile}",
        "mlir": "codegen/aie/aie.mlir",
        "mapping": "codegen/aie/mapping.json",
        "fifos": "codegen/aie/fifos.json",
        "host": "codegen/aie/host.py",
    }
    toolchain = {
        "schema": AIE_TOOLCHAIN_SCHEMA_ID,
        "toolchain_contract": "mlir-aie:dev",
        "profile": profile,
        "build_driver": {
            "kind": "python_module",
            "module": "htp_ext.aie.toolchain",
            "callable": "build_package",
        },
        "build_product_schema": AIE_BUILD_PRODUCT_SCHEMA_ID,
        "host_runtime_schema": AIE_HOST_RUNTIME_SCHEMA_ID,
        "derived_outputs": [
            "build/aie/build_product.json",
            "build/aie/host_runtime.json",
            "build/aie/launch_plan.json",
        ],
        "build_flags": [],
    }

    (codegen_dir / "aie.mlir").write_text("\n".join(mlir_lines) + "\n")
    (codegen_dir / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (codegen_dir / "fifos.json").write_text(json.dumps(fifos, indent=2) + "\n")
    (codegen_dir / "host.py").write_text(host)
    (codegen_dir / "aie_codegen.json").write_text(json.dumps(codegen_index, indent=2) + "\n")
    (codegen_dir / "toolchain.json").write_text(json.dumps(toolchain, indent=2) + "\n")


def _render_aie_mlir(
    *,
    state: Mapping[str, Any],
    mapping: Mapping[str, Any],
    fifos: Mapping[str, Any],
    profile: str,
) -> list[str]:
    lines = [
        "module {",
        f'  aie.device("{profile}") {{',
    ]
    tile_symbols: dict[str, str] = {}
    for tile in mapping.get("tiles", ()):
        task_id = str(tile["task_id"])
        row, col = tile["coords"]
        symbol = f"%tile_{row}_{col}"
        tile_symbols[task_id] = symbol
        lines.append(f"    {symbol} = aie.tile({row}, {col})")
    for fifo in fifos.get("channels", ()):
        producers = list(fifo.get("producers", ()))
        consumers = list(fifo.get("consumers", ()))
        if not producers or not consumers:
            continue
        producer_symbol = tile_symbols.get(str(producers[0]["task_id"]), "%tile_0_0")
        consumer_symbols = ", ".join(
            tile_symbols.get(str(item["task_id"]), "%tile_0_0") for item in consumers
        )
        lines.append(
            "    "
            f"aie.objectfifo @{fifo['name']}({producer_symbol}, {{{consumer_symbols}}}, "
            f"{int(fifo['capacity'])} : {fifo['dtype']})"
        )
    lines.append(f"    func.func @{state['entry']}() {{")
    for tile in mapping.get("tiles", ()):
        lines.append(
            "      "
            f"// task {tile['task_id']} kernel={tile['kernel']} tile={tuple(tile['coords'])} memory={tile['memory_space']}"
        )
    for fifo in fifos.get("channels", ()):
        producer_names = [str(item["task_id"]) for item in fifo.get("producers", ())]
        consumer_names = [str(item["task_id"]) for item in fifo.get("consumers", ())]
        lines.append(
            "      "
            f"// fifo {fifo['name']} producers={producer_names!r} consumers={consumer_names!r} protocol={fifo['protocol']}"
        )
    lines.extend(("      return", "    }", "  }", "}"))
    return lines


__all__ = [
    "AIE_CODEGEN_SCHEMA_ID",
    "AIE_PROJECT_DIR",
    "AIE_TOOLCHAIN_SCHEMA_ID",
    "emit_package",
]
