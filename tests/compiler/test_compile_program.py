import json

import htp


def _vector_add_program() -> dict[str, object]:
    return {
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
    }


def test_compile_program_emits_pto_package_and_keeps_stage_replay(tmp_path):
    package_dir = tmp_path / "pto_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="pto-a2a3sim",
        program=_vector_add_program(),
    )

    assert compiled.target.backend == "pto"
    assert compiled.manifest["target"] == {
        "backend": "pto",
        "variant": "a2a3sim",
        "hardware_profile": "ascend:a2a3sim",
    }
    assert compiled.pipeline.current_stage == "s06"

    session = htp.bind(package_dir).load(mode="sim")
    replay = session.replay(compiled.pipeline.current_stage)
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["target"] == {"backend": "pto", "option": "a2a3sim"}
    assert replay.result["kernel_ir"]["ops"][0]["op"] == "elementwise_binary"


def test_compile_program_emits_nvgpu_package_and_keeps_stage_replay(tmp_path):
    package_dir = tmp_path / "nvgpu_pkg"

    compiled = htp.compile_program(
        package_dir=package_dir,
        target="nvgpu-ampere",
        program={
            "entry": "gemm_tile",
            "kernel": {
                "name": "gemm_tile",
                "args": [
                    {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
                    {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
                    {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
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
                "entry": "gemm_tile",
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": "gemm_tile",
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

    assert compiled.target.backend == "nvgpu"
    assert compiled.manifest["target"] == {
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:ampere:sm80",
    }
    assert json.loads((package_dir / "manifest.json").read_text()) == compiled.manifest

    session = htp.bind(package_dir).load(mode="sim")
    replay = session.replay(compiled.pipeline.current_stage)
    assert replay.ok is True
    assert replay.result["package"]["emitted"] is True
    assert replay.result["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert replay.result["kernel_ir"]["ops"][0]["op"] == "matmul"


def test_compile_program_rejects_unknown_targets(tmp_path):
    package_dir = tmp_path / "bad_pkg"

    try:
        htp.compile_program(
            package_dir=package_dir,
            target="aie-xdna2",
        )
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
