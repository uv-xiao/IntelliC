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
from htp.schemas import MANIFEST_SCHEMA_ID

from .declarations import CPU_REF_PROJECT_DIR, CPU_REF_TOOLCHAIN_PATH, declaration_for

CPU_REF_CODEGEN_SCHEMA_ID = "htp.cpu_ref.codegen.v1"
CPU_REF_TOOLCHAIN_SCHEMA_ID = "htp.cpu_ref.toolchain.v1"


def emit_package(
    package_dir: Path | str,
    *,
    program: Mapping[str, Any],
) -> dict[str, Any]:
    package_path = Path(package_dir)
    package_path.mkdir(parents=True, exist_ok=True)
    state = _semanticize_program(program)
    _write_codegen_tree(package_path, state=state)
    manifest = _load_or_seed_manifest(package_path, state)
    manifest["schema"] = MANIFEST_SCHEMA_ID
    manifest["target"] = {
        "backend": "cpu_ref",
        "variant": "python",
        "hardware_profile": "host:python:numpy",
    }
    manifest["outputs"] = declaration_for().artifact_contract.as_manifest_outputs()
    manifest["extensions"] = {
        "cpu_ref": {
            "toolchain_contract": "python:numpy",
            "launch_entry": {
                "source": (CPU_REF_PROJECT_DIR / "reference.py").as_posix(),
                "function_name": f"launch_{state['entry']}",
            },
            "toolchain_manifest": CPU_REF_TOOLCHAIN_PATH.as_posix(),
        }
    }
    manifest_path = package_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _semanticize_program(program: Mapping[str, Any]) -> dict[str, Any]:
    state = dict(program)
    state["target"] = {"backend": "cpu_ref", "option": "python"}
    state["analysis"] = dict(state.get("analysis", {}))
    state["package"] = {"emitted": True, "backend": "cpu_ref", "entry": str(program["entry"])}
    state["canonical_ast"] = canonicalize_program(state)
    kernel_ir, workload_ir, entities_payload, bindings_payload = build_semantic_model(state["canonical_ast"])
    state["kernel_ir"] = kernel_ir
    state["workload_ir"] = workload_ir
    state["entities_payload"] = entities_payload
    state["bindings_payload"] = bindings_payload
    types, layout, effects = build_type_layout_effects(
        kernel_ir, workload_ir, target={"backend": "cpu_ref", "option": "python"}
    )
    state["types"] = types
    state["layout"] = layout
    state["effects"] = effects
    schedule_plan = build_schedule_plan(
        entry=str(program["entry"]),
        kernel_ir=kernel_ir,
        effects=effects,
        target={"backend": "cpu_ref", "option": "python"},
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
            pass_id="htp_ext.cpu_ref::emit@1",
            runnable_py=RunnablePySpec(
                status="preserves",
                modes=("sim",),
                program_text=render_program_state_module(state),
            ),
            analyses=(),
            program_module_payload=payloads["program_module_payload"],
        ),
    )
    return write_manifest(package_path, current_stage=stage_id, stages=[*existing_stages, stage])


def _write_codegen_tree(package_dir: Path, *, state: Mapping[str, Any]) -> None:
    codegen_dir = package_dir / CPU_REF_PROJECT_DIR
    codegen_dir.mkdir(parents=True, exist_ok=True)
    entry = str(state["entry"])
    reference_relpath = (CPU_REF_PROJECT_DIR / "reference.py").as_posix()
    codegen_index = {
        "schema": CPU_REF_CODEGEN_SCHEMA_ID,
        "entrypoint": entry,
        "variant": "python",
        "hardware_profile": "host:python:numpy",
        "launch": {
            "source": reference_relpath,
            "function_name": f"launch_{entry}",
        },
        "kernel_ir": "ir/stages/s01/state.json#/items/kernel_ir",
    }
    toolchain = {
        "schema": CPU_REF_TOOLCHAIN_SCHEMA_ID,
        "toolchain_contract": "python:numpy",
        "build_driver": {
            "kind": "python_module",
            "module": "htp.bindings.cpu_ref",
            "callable": "build_reference_runtime",
        },
        "derived_outputs": [
            "build/cpu_ref/runtime.json",
        ],
    }
    (codegen_dir / "reference.py").write_text(_render_reference_module(state))
    (codegen_dir / "cpu_ref_codegen.json").write_text(json.dumps(codegen_index, indent=2) + "\n")
    (package_dir / CPU_REF_TOOLCHAIN_PATH).parent.mkdir(parents=True, exist_ok=True)
    (package_dir / CPU_REF_TOOLCHAIN_PATH).write_text(json.dumps(toolchain, indent=2) + "\n")


def _render_reference_module(state: Mapping[str, Any]) -> str:
    entry = str(state["entry"])
    kernel_ir = state["kernel_ir"]
    args = list(kernel_ir.get("args", ()))
    ops = list(kernel_ir.get("ops", ()))
    arg_names = [str(arg["name"]) for arg in args]
    bind_lines = [f"    {name} = args[{index}]" for index, name in enumerate(arg_names)]
    env_lines = [f'        "{name}": {name},' for name in arg_names]
    statements = [
        "def _unary(op, value):",
        '    if op == "identity":',
        "        return value",
        '    if op == "neg":',
        "        return -value",
        '    if op == "relu":',
        "        return np.maximum(value, 0)",
        '    if op == "sigmoid":',
        "        return 1.0 / (1.0 + np.exp(-value))",
        '    if op == "exp":',
        "        return np.exp(value)",
        '    raise ValueError(f"unsupported unary op: {op}")',
        "",
        "def _binary(op, lhs, rhs):",
        '    if op == "add":',
        "        return lhs + rhs",
        '    if op == "sub":',
        "        return lhs - rhs",
        '    if op == "mul":',
        "        return lhs * rhs",
        '    if op == "div":',
        "        return lhs / rhs",
        '    raise ValueError(f"unsupported binary op: {op}")',
        "",
        f"def launch_{entry}(*args, mode='sim', trace='off', runtime=None):",
        "    del mode, trace, runtime",
        f"    if len(args) != {len(arg_names)}:",
        f"        raise TypeError('expected {len(arg_names)} positional args for {entry}')",
        *bind_lines,
        "    env = {",
        *env_lines,
        "    }",
    ]
    for op in ops:
        statements.extend(_render_op(op, args=args))
    statements.extend(
        [
            "    return {",
            "        'adapter': 'cpu-ref',",
            f"        'entry': {entry!r},",
            "        'outputs': {name: np.asarray(env[name]).tolist() for name in env if isinstance(env.get(name), np.ndarray)},",
            "    }",
            "",
        ]
    )
    return "\n".join(["from __future__ import annotations", "", "import numpy as np", "", *statements, ""])


def _render_op(op: Mapping[str, Any], *, args: list[dict[str, Any]]) -> list[str]:
    op_name = str(op.get("op", ""))
    attrs = op.get("attrs", {}) if isinstance(op.get("attrs"), Mapping) else {}
    outputs = op.get("outputs", attrs.get("outputs", ()))
    output_name = str(
        op.get("out", attrs.get("out", outputs[0] if isinstance(outputs, list) and outputs else ""))
    )
    if op_name == "elementwise_binary":
        inputs = op.get("inputs", attrs.get("inputs", ()))
        lhs = str(
            op.get(
                "lhs", attrs.get("lhs", inputs[0] if isinstance(inputs, list) and len(inputs) > 0 else "lhs")
            )
        )
        rhs = str(
            op.get(
                "rhs", attrs.get("rhs", inputs[1] if isinstance(inputs, list) and len(inputs) > 1 else "rhs")
            )
        )
        operator = str(op.get("operator", attrs.get("operator", "add")))
        return _assign_result(output_name, f"_binary({operator!r}, env[{lhs!r}], env[{rhs!r}])", args=args)
    if op_name == "elementwise_unary":
        inputs = op.get("inputs", attrs.get("inputs", ()))
        src = str(
            op.get("src", attrs.get("src", inputs[0] if isinstance(inputs, list) and inputs else "src"))
        )
        operator = str(op.get("operator", attrs.get("operator", "neg")))
        return _assign_result(output_name, f"_unary({operator!r}, env[{src!r}])", args=args)
    if op_name == "matmul":
        inputs = op.get("inputs", attrs.get("inputs", ()))
        lhs = str(
            op.get(
                "lhs", attrs.get("lhs", inputs[0] if isinstance(inputs, list) and len(inputs) > 0 else "A")
            )
        )
        rhs = str(
            op.get(
                "rhs", attrs.get("rhs", inputs[1] if isinstance(inputs, list) and len(inputs) > 1 else "B")
            )
        )
        return _assign_result(output_name, f"np.matmul(env[{lhs!r}], env[{rhs!r}])", args=args)
    if op_name == "reduction_sum":
        inputs = op.get("inputs", attrs.get("inputs", ()))
        src = str(
            op.get("src", attrs.get("src", inputs[0] if isinstance(inputs, list) and inputs else "src"))
        )
        axis = op.get("axis", attrs.get("axis"))
        axis_expr = "None" if axis is None else repr(axis)
        return _assign_result(output_name, f"np.sum(env[{src!r}], axis={axis_expr})", args=args)
    if op_name == "broadcast":
        inputs = op.get("inputs", attrs.get("inputs", ()))
        src = str(
            op.get("src", attrs.get("src", inputs[0] if isinstance(inputs, list) and inputs else "src"))
        )
        shape = list(op.get("shape", attrs.get("shape", [])))
        return _assign_result(output_name, f"np.broadcast_to(env[{src!r}], {shape!r})", args=args)
    if op_name == "transpose":
        inputs = op.get("inputs", attrs.get("inputs", ()))
        src = str(
            op.get("src", attrs.get("src", inputs[0] if isinstance(inputs, list) and inputs else "src"))
        )
        axes = op.get("axes", attrs.get("axes"))
        axes_expr = "None" if axes is None else repr(tuple(axes))
        return _assign_result(output_name, f"np.transpose(env[{src!r}], axes={axes_expr})", args=args)
    if op_name == "cast":
        inputs = op.get("inputs", attrs.get("inputs", ()))
        src = str(
            op.get("src", attrs.get("src", inputs[0] if isinstance(inputs, list) and inputs else "src"))
        )
        dtype = str(op.get("dtype", attrs.get("dtype", "float32")))
        numpy_dtype = {"f32": "np.float32", "f64": "np.float64", "i32": "np.int32", "i64": "np.int64"}.get(
            dtype, "np.float32"
        )
        return _assign_result(output_name, f"env[{src!r}].astype({numpy_dtype})", args=args)
    return [f"    # unsupported cpu_ref op preserved for visibility: {op_name}"]


def _assign_result(target: str, expr: str, *, args: list[dict[str, Any]]) -> list[str]:
    target_arg = next((arg for arg in args if str(arg.get("name")) == target), None)
    if target_arg is not None and str(target_arg.get("role")) in {"output", "inout"}:
        return [
            f"    _value = {expr}",
            f"    np.copyto(env[{target!r}], np.asarray(_value, dtype=env[{target!r}].dtype))",
        ]
    return [f"    env[{target!r}] = {expr}"]


__all__ = ["CPU_REF_CODEGEN_SCHEMA_ID", "CPU_REF_TOOLCHAIN_SCHEMA_ID", "emit_package"]
