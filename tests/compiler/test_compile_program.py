from __future__ import annotations

import json
from pathlib import Path

import htp
from htp.ir.frontend_rules import FrontendBuildContext, FrontendRule, FrontendRuleResult
from htp.ir.frontends import FrontendSpec, register_frontend
from htp.ir.module import ProgramModule
from htp.pipeline.defaults import MANDATORY_PASS_IDS
from tests.programs import nvgpu_serving_program, portable_vector_add_program, pto_vector_dag_program


class DemoSurface:
    def __init__(self, entry: str) -> None:
        self.entry = entry


def test_compile_program_emits_pto_package_and_keeps_stage_replay(tmp_path):
    package_dir = tmp_path / "pto_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="pto-a2a3sim",
        program=pto_vector_dag_program(),
    )

    assert compiled.target.backend == "pto"
    assert compiled.manifest["target"] == {
        "backend": "pto",
        "variant": "a2a3sim",
        "hardware_profile": "ascend:a2a3sim",
        "option": "a2a3sim",
    }
    assert compiled.manifest["inputs"]["entry"] == "vector_dag"
    assert compiled.manifest["pipeline"]["pass_ids"] == list(MANDATORY_PASS_IDS)
    assert compiled.manifest["capabilities"]["target"]["backend"] == "pto"
    assert compiled.pipeline.current_stage == f"s{len(MANDATORY_PASS_IDS):02d}"

    session = htp.bind(package_dir).load(mode="sim")
    replay = session.replay(compiled.pipeline.current_stage)
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["target"] == {"backend": "pto", "option": "a2a3sim"}
    assert len(replay.result["kernel_ir"]["ops"]) >= 5
    assert replay.result["kernel_ir"]["ops"][0]["op"] == "elementwise_binary"


def test_compile_program_emits_pto_device_package(tmp_path):
    package_dir = tmp_path / "pto_device_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="pto-a2a3",
        program=pto_vector_dag_program(),
    )

    assert compiled.target.backend == "pto"
    assert compiled.manifest["target"] == {
        "backend": "pto",
        "variant": "a2a3",
        "hardware_profile": "ascend:a2a3",
        "option": "a2a3",
    }
    toolchain_manifest = json.loads((package_dir / "build" / "toolchain.json").read_text())
    assert toolchain_manifest["compiler_contract"] == "cann:stub"


def test_compile_program_emits_nvgpu_package_and_keeps_stage_replay(tmp_path):
    package_dir = tmp_path / "nvgpu_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="nvgpu-ampere",
        program=nvgpu_serving_program(),
    )

    assert compiled.target.backend == "nvgpu"
    assert compiled.manifest["target"] == {
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:ampere:sm80",
        "option": "ampere",
    }
    assert compiled.manifest["pipeline"]["template_id"] == "htp.default.v1"
    assert compiled.manifest["capabilities"]["target"]["backend"] == "nvgpu"
    assert json.loads((package_dir / "manifest.json").read_text()) == compiled.manifest

    session = htp.bind(package_dir).load(mode="sim")
    replay = session.replay(compiled.pipeline.current_stage)
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert "matmul" in [op["op"] for op in replay.result["kernel_ir"]["ops"]]
    assert [task["task_id"] for task in replay.result["workload_ir"]["tasks"][:2]] == [
        "prefill",
        "decode_step_0",
    ]


def test_compile_program_emits_aie_package_and_keeps_stage_replay(tmp_path):
    package_dir = tmp_path / "aie_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="aie-xdna2-npu1",
        program={
            "entry": "vector_add",
            "kernel": {
                "name": "vector_add",
                "args": [
                    {"name": "lhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                    {"name": "rhs", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "input"},
                    {"name": "out", "kind": "buffer", "dtype": "f32", "shape": ["size"], "role": "output"},
                    {"name": "size", "kind": "scalar", "dtype": "i32", "role": "shape"},
                ],
                "ops": [
                    {
                        "op": "elementwise_binary",
                        "operator": "add",
                        "lhs": "lhs",
                        "rhs": "rhs",
                        "out": "out",
                        "shape": ["size"],
                        "dtype": "f32",
                    }
                ],
            },
            "workload": {
                "entry": "vector_add",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "vector_add",
                        "args": ["lhs", "rhs", "out", "size"],
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
            "analysis": {},
            "package": {"emitted": False},
        },
    )

    assert compiled.target.backend == "aie"
    assert compiled.manifest["target"] == {
        "backend": "aie",
        "variant": "mlir-aie",
        "hardware_profile": "amd-xdna2:xdna2-npu1",
        "option": "xdna2-npu1",
    }
    assert compiled.manifest["outputs"] == {
        "aie_codegen_index": "codegen/aie/aie_codegen.json",
        "toolchain_manifest": "codegen/aie/toolchain.json",
    }

    replay = htp.bind(package_dir).load(mode="sim").replay(compiled.pipeline.current_stage)
    assert replay.ok is True
    assert replay.result["target"] == {"backend": "aie", "option": "xdna2-npu1"}
    assert replay.result["package"]["emitted"] is True


def test_compile_program_emits_cpu_ref_package(tmp_path):
    package_dir = tmp_path / "cpu_ref_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="cpu_ref",
        program=portable_vector_add_program(),
    )

    assert compiled.target.backend == "cpu_ref"
    assert compiled.manifest["target"] == {
        "backend": "cpu_ref",
        "variant": "python",
        "hardware_profile": "host:python:numpy",
    }
    assert compiled.manifest["outputs"] == {
        "cpu_ref_codegen_index": "codegen/cpu_ref/cpu_ref_codegen.json",
        "toolchain_manifest": "build/toolchain.json",
    }


def test_compile_program_rejects_unknown_targets(tmp_path):
    package_dir = tmp_path / "bad_pkg"

    try:
        htp.compile_program(package_dir=package_dir, target="unknown-x")
    except ValueError as exc:
        assert "Unsupported target backend" in str(exc)
    else:
        raise AssertionError("compile_program should reject unsupported backends")


def test_compile_program_writes_solver_failure_for_unsupported_backend_op(tmp_path):
    package_dir = tmp_path / "bad_pkg"

    try:
        htp.compile_program(
            package_dir=package_dir,
            target="pto-a2a3sim",
            program={
                "entry": "channel_kernel",
                "kernel": {
                    "name": "channel_kernel",
                    "args": [
                        {"name": "value", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                        {"name": "channel", "kind": "scalar", "dtype": "i32", "shape": [], "role": "input"},
                    ],
                    "ops": [
                        {"op": "channel_send", "value": "value", "channel": "channel", "outputs": []},
                    ],
                },
                "workload": {
                    "entry": "channel_kernel",
                    "tasks": [
                        {
                            "task_id": "task0",
                            "kind": "kernel_call",
                            "kernel": "channel_kernel",
                            "args": ["value", "channel"],
                        }
                    ],
                    "channels": [{"name": "channel", "dtype": "i32"}],
                    "dependencies": [],
                },
                "analysis": {},
                "package": {"emitted": False},
            },
        )
    except RuntimeError as exc:
        assert "solver" in str(exc).lower()
    else:
        raise AssertionError("compile_program should reject unsupported backend operations")

    failure = json.loads((package_dir / "ir" / "solver_failure.json").read_text())
    assert failure["failed_at_pass"] == "target.handlers"
    assert failure["missing_handlers"] == [{"backend": "pto", "op": "channel_send"}]


def test_compile_program_writes_compiler_failure_for_layout_typecheck(tmp_path):
    package_dir = tmp_path / "bad_pkg"

    try:
        htp.compile_program(
            package_dir=package_dir,
            target="nvgpu-ampere",
            program={
                "entry": "bad_kernel",
                "kernel": {
                    "name": "bad_kernel",
                    "args": [
                        {
                            "name": "A",
                            "kind": "buffer",
                            "dtype": "f16",
                            "shape": ["M", "K"],
                            "role": "input",
                        },
                        {
                            "name": "B",
                            "kind": "buffer",
                            "dtype": "f32",
                            "shape": ["K", "N"],
                            "role": "input",
                        },
                        {
                            "name": "C",
                            "kind": "buffer",
                            "dtype": "f32",
                            "shape": ["M", "N"],
                            "role": "output",
                        },
                        {"name": "M", "kind": "scalar", "dtype": "i32", "role": "shape"},
                        {"name": "N", "kind": "scalar", "dtype": "i32", "role": "shape"},
                        {"name": "K", "kind": "scalar", "dtype": "i32", "role": "shape"},
                    ],
                    "ops": [
                        {
                            "op": "matmul",
                            "lhs": "A",
                            "rhs": "B",
                            "out": "C",
                            "m": "M",
                            "n": "N",
                            "k": "K",
                            "dtype": "f32",
                        }
                    ],
                },
                "workload": {
                    "entry": "bad_kernel",
                    "tasks": [
                        {
                            "task_id": "task0",
                            "kind": "kernel_call",
                            "kernel": "bad_kernel",
                            "args": ["A", "B", "C", "M", "N", "K"],
                        }
                    ],
                    "channels": [],
                    "dependencies": [],
                },
                "analysis": {},
                "package": {"emitted": False},
            },
        )
    except RuntimeError as exc:
        assert "Compiler failed at htp::typecheck_layout_effects@1" in str(exc)
    else:
        raise AssertionError("compile_program should reject unsupported layout/type combinations")

    failure = json.loads((package_dir / "ir" / "compiler_failure.json").read_text())
    assert failure == {
        "schema": "htp.compiler_failure.v1",
        "failed_at_pass": "htp::typecheck_layout_effects@1",
        "stage_before": "s02",
        "diagnostic": {
            "code": "HTP.TYPECHECK.UNSUPPORTED_BUFFER_DTYPE",
            "detail": "nvgpu buffer 'A' requires one of ['bf16', 'f32'], got 'f16'.",
            "node_id": "bad_kernel:Arg:0",
            "entity_id": "bad_kernel:E0",
            "stage_id": "s02",
            "pass_id": "htp::typecheck_layout_effects@1",
            "payload_ref": "ir/stages/s02/state.json#/items/kernel_ir",
            "fix_hints_ref": "docs/design/compiler_model.md",
            "backend": "nvgpu",
            "manifest_value": "f16",
        },
    }


def test_compile_program_writes_compiler_failure_for_protocol_violation(tmp_path):
    package_dir = tmp_path / "bad_protocol_pkg"

    try:
        htp.compile_program(
            package_dir=package_dir,
            target="pto-a2a3sim",
            program={
                "entry": "channel_kernel",
                "kernel": {
                    "name": "channel_kernel",
                    "args": [],
                    "ops": [],
                },
                "workload": {
                    "entry": "channel_kernel",
                    "tasks": [],
                    "channels": [{"name": "pipe0", "dtype": "i32", "capacity": 1, "protocol": "fifo"}],
                    "dependencies": [],
                    "processes": [
                        {
                            "name": "producer",
                            "task_id": "task0",
                            "kernel": "channel_kernel",
                            "puts": [{"channel": "pipe0", "count": 2}],
                            "gets": [],
                        }
                    ],
                },
                "analysis": {},
                "package": {"emitted": False},
            },
        )
    except RuntimeError as exc:
        assert "Compiler failed at htp::typecheck_layout_effects@1" in str(exc)
    else:
        raise AssertionError("compile_program should reject unbalanced protocol obligations")

    failure = json.loads((package_dir / "ir" / "compiler_failure.json").read_text())
    assert failure["failed_at_pass"] == "htp::typecheck_layout_effects@1"
    assert failure["diagnostic"]["code"] == "HTP.PROTOCOL.UNBALANCED_CHANNEL"
    assert failure["diagnostic"]["node_id"] == "channel_kernel:Channel:0"
    assert failure["diagnostic"]["payload_ref"] == "ir/stages/s02/state.json#/items/workload_ir"
    assert failure["diagnostic"]["channel"] == "pipe0"
    assert failure["diagnostic"]["puts"] == 2
    assert failure["diagnostic"]["gets"] == 0


def test_compile_program_uses_registered_frontend_rule(tmp_path: Path) -> None:
    def build_demo(context: FrontendBuildContext) -> FrontendRuleResult:
        module = ProgramModule.from_program_dict(
            {
                "entry": context.surface.entry,
                "canonical_ast": {
                    "schema": "htp.program_ast.v1",
                    "program": {"entry": context.surface.entry},
                },
                "kernel_ir": {},
                "workload_ir": {},
                "target": {"backend": "cpu_ref"},
            },
            meta={"source_surface": "demo.rule"},
        )
        return FrontendRuleResult(module=module)

    register_frontend(
        FrontendSpec(
            frontend_id="demo.surface",
            dialect_id="htp.core",
            surface_type=DemoSurface,
            rule=FrontendRule(name="build_demo", build=build_demo),
        ),
        replace=True,
    )

    compiled = htp.compile_program(
        package_dir=tmp_path / "demo_surface_pkg",
        target="cpu_ref",
        program=DemoSurface("demo_entry"),
    )

    assert compiled.manifest["inputs"]["entry"] == "demo_entry"
