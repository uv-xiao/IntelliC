import numpy as np

from htp.backends.pto.emit import emit_package
from htp.bindings import pto_runtime_adapter
from htp.bindings.api import bind


def test_pto_build_returns_structured_result(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "kernel": {
                "name": "demo_kernel",
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
        },
    )

    monkeypatch.setattr(
        pto_runtime_adapter,
        "build_package",
        lambda *args, **kwargs: (
            [
                "build/pto/runtime/libhost_runtime.so",
                "build/pto/runtime/libaicpu_runtime.so",
                "build/pto/runtime/aicore_runtime.bin",
                "build/pto/orchestration/demo_kernel_orchestration.so",
                "build/pto/kernels/0.bin",
            ],
            [],
        ),
    )

    result = bind(package_dir).build(mode="sim")

    assert result.ok is True
    assert result.mode == "sim"
    assert result.built_outputs == [
        "build/pto/runtime/libhost_runtime.so",
        "build/pto/runtime/libaicpu_runtime.so",
        "build/pto/runtime/aicore_runtime.bin",
        "build/pto/orchestration/demo_kernel_orchestration.so",
        "build/pto/kernels/0.bin",
    ]
    assert len(result.log_paths) == 1
    assert result.diagnostics == []


def test_pto_run_executes_through_adapter(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "kernel": {
                "name": "demo_kernel",
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
        },
    )

    monkeypatch.setattr(
        pto_runtime_adapter,
        "run_package",
        lambda *args, **kwargs: (
            True,
            {"adapter": "pto-runtime", "platform": "a2a3sim", "output_names": ["out"]},
            [],
        ),
    )

    session = bind(package_dir).load(mode="sim")
    result = session.run(
        "demo_kernel",
        args=(
            np.arange(16, dtype=np.float32),
            np.arange(16, dtype=np.float32),
            np.zeros(16, dtype=np.float32),
            16,
        ),
    )

    assert result.ok is True
    assert result.mode == "sim"
    assert result.entry == "demo_kernel"
    assert result.result == {"adapter": "pto-runtime", "platform": "a2a3sim", "output_names": ["out"]}
    assert result.diagnostics == []
    assert result.log_path is not None
