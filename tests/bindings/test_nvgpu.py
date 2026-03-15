import json

import numpy as np

import htp.runtime as runtime_api
from examples.wsp_warp_gemm.demo import compile_example as compile_wsp_example
from htp.backends.nvgpu.emit import emit_package
from htp.bindings import nvgpu_cuda_adapter
from htp.bindings.api import bind


def _gemm_program() -> dict[str, object]:
    return {
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
    }


def test_nvgpu_build_reports_source_and_derived_outputs(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")

    result = bind(package_dir).build(mode="sim")

    assert result.ok is True
    assert result.mode == "sim"
    assert result.built_outputs == [
        "codegen/nvgpu/nvgpu_codegen.json",
        "build/toolchain.json",
        "codegen/nvgpu/host/gemm_tile_launch.py",
        "codegen/nvgpu/kernels/gemm_tile.cu",
        "build/nvgpu/gemm_tile.ptx",
        "build/nvgpu/gemm_tile.cubin",
    ]
    assert len(result.log_paths) == 1
    assert result.trace_refs == []
    assert result.diagnostics == []


def test_nvgpu_run_uses_launch_entry_and_runtime(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")

    runtime = runtime_api.Runtime()
    runtime.register_kernel(
        "gemm_tile.kernel0",
        lambda *, args, mode, artifacts, trace=None: {
            "args": args,
            "mode": mode,
            "artifacts": dict(artifacts),
            "trace": trace,
        },
    )
    monkeypatch.setattr(runtime_api, "default_runtime", lambda: runtime)

    session = bind(package_dir).load(mode="sim")
    a = np.ones((4, 4), dtype=np.float32)
    b = np.ones((4, 4), dtype=np.float32)
    c = np.zeros((4, 4), dtype=np.float32)
    result = session.run("gemm_tile", args=(a, b, c, 4, 4, 4), trace="basic")

    assert result.ok is True
    assert result.mode == "sim"
    assert result.entry == "launch_gemm_tile"
    assert result.result == {
        "args": (a, b, c, 4, 4, 4),
        "mode": "sim",
        "artifacts": {
            "backend": "nvgpu",
            "variant": "cuda",
            "hardware_profile": "nvidia:ampere:sm80",
            "kernel_source": "codegen/nvgpu/kernels/gemm_tile.cu",
            "kernel_params": ["A", "B", "C", "M", "N", "K"],
        },
        "trace": "basic",
    }
    assert result.diagnostics == []
    assert result.log_path is not None


def test_nvgpu_device_build_uses_cuda_adapter(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")

    monkeypatch.setattr(
        nvgpu_cuda_adapter,
        "build_package",
        lambda *args, **kwargs: (
            ["build/nvgpu/gemm_tile.ptx", "build/nvgpu/gemm_tile.cubin"],
            [],
            "logs/adapter_nvgpu_build.json",
        ),
    )

    result = bind(package_dir).build(mode="device")

    assert result.ok is True
    assert result.mode == "device"
    assert result.built_outputs == [
        "codegen/nvgpu/nvgpu_codegen.json",
        "build/toolchain.json",
        "codegen/nvgpu/host/gemm_tile_launch.py",
        "codegen/nvgpu/kernels/gemm_tile.cu",
        "build/nvgpu/gemm_tile.ptx",
        "build/nvgpu/gemm_tile.cubin",
    ]
    assert result.trace_refs == ["logs/adapter_nvgpu_build.json"]
    assert result.diagnostics == []


def test_nvgpu_device_run_uses_cuda_adapter(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")

    monkeypatch.setattr(
        nvgpu_cuda_adapter,
        "run_package",
        lambda *args, **kwargs: (
            True,
            {
                "adapter": "cuda_driver",
                "entry": "gemm_tile",
                "kernel": "gemm_tile_kernel0",
                "cubin": "build/nvgpu/gemm_tile.cubin",
                "thread_block": [16, 16, 1],
                "grid": [1, 1, 1],
                "params": ["A", "B", "C", "M", "N", "K"],
                "trace_ref": "logs/adapter_nvgpu_run.json",
            },
            [],
            "logs/adapter_nvgpu_run.json",
        ),
    )

    a = np.ones((4, 4), dtype=np.float32)
    b = np.ones((4, 4), dtype=np.float32)
    c = np.zeros((4, 4), dtype=np.float32)
    result = bind(package_dir).load(mode="device").run("gemm_tile", args=(a, b, c, 4, 4, 4))

    assert result.ok is True
    assert result.mode == "device"
    assert result.entry == "launch_gemm_tile"
    assert result.result == {
        "adapter": "cuda_driver",
        "entry": "gemm_tile",
        "kernel": "gemm_tile_kernel0",
        "cubin": "build/nvgpu/gemm_tile.cubin",
        "thread_block": [16, 16, 1],
        "grid": [1, 1, 1],
        "params": ["A", "B", "C", "M", "N", "K"],
        "trace_ref": "logs/adapter_nvgpu_run.json",
    }
    assert result.trace_ref == "logs/adapter_nvgpu_run.json"
    assert result.diagnostics == []


def test_nvgpu_validate_reports_artifact_ref_for_invalid_codegen_schema(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")

    codegen_path = package_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json"
    payload = json.loads(codegen_path.read_text())
    payload["schema"] = "broken.schema"
    codegen_path.write_text(json.dumps(payload, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert any(
        diagnostic.get("code") == "HTP.BINDINGS.INVALID_SCHEMA"
        and diagnostic.get("artifact_ref") == "codegen/nvgpu/nvgpu_codegen.json"
        for diagnostic in report.diagnostics
    )


def test_nvgpu_binding_replays_wsp_slice_views_in_sim_mode(tmp_path):
    package_dir = tmp_path / "wsp_example"
    compile_wsp_example(package_dir)

    session = bind(package_dir).load(mode="sim")
    stage_id = session.manifest["stages"]["current"]
    result = session.replay(stage_id)

    assert result.ok is True
    assert result.stage_id == stage_id
    assert result.diagnostics == []
