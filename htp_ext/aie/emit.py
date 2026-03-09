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
from htp.passes.replay_program import render_program_state_module
from htp_ext.aie.declarations import AIE_PROJECT_DIR, declaration_for

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
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if isinstance(manifest.get("stages"), Mapping):
            return manifest
    payloads = stage_payloads_from_program(state)
    stage = write_stage(
        package_path,
        StageSpec(
            stage_id="s01",
            pass_id="htp_ext.aie::emit@1",
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text=render_program_state_module(state),
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
    return write_manifest(package_path, current_stage="s01", stages=[stage])


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

    channels = state["effects"]["channels"]
    mapping = {
        "schema": "htp.aie.mapping.v1",
        "entry": state["entry"],
        "profile": profile,
        "tiles": [
            {"task_id": task["task_id"], "tile": [0, index]}
            for index, task in enumerate(state["workload_ir"]["tasks"])
        ],
    }
    fifos = {
        "schema": "htp.aie.fifos.v1",
        "entry": state["entry"],
        "channels": channels,
    }
    host = "\n".join(
        (
            f"ENTRY = {state['entry']!r}",
            "def launch(*args, **kwargs):",
            "    del args, kwargs",
            "    return {'status': 'sim-only'}",
            "",
        )
    )
    mlir_lines = [
        "module {",
        f"  // profile: {profile}",
        f"  func.func @{state['entry']}() {{",
    ]
    for task in state["workload_ir"]["tasks"]:
        mlir_lines.append(f"    // task {task['task_id']} -> {task['kernel']}")
    for channel in channels:
        mlir_lines.append(f"    // fifo {channel['name']} dtype={channel['dtype']} kind={channel['kind']}")
    mlir_lines.extend(("    return", "  }", "}"))
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
        "build_flags": [],
    }

    (codegen_dir / "aie.mlir").write_text("\n".join(mlir_lines) + "\n")
    (codegen_dir / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (codegen_dir / "fifos.json").write_text(json.dumps(fifos, indent=2) + "\n")
    (codegen_dir / "host.py").write_text(host)
    (codegen_dir / "aie_codegen.json").write_text(json.dumps(codegen_index, indent=2) + "\n")
    (codegen_dir / "toolchain.json").write_text(json.dumps(toolchain, indent=2) + "\n")


__all__ = [
    "AIE_CODEGEN_SCHEMA_ID",
    "AIE_PROJECT_DIR",
    "AIE_TOOLCHAIN_SCHEMA_ID",
    "emit_package",
]
