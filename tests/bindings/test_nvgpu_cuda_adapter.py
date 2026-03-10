from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from htp.backends.nvgpu.emit import emit_package
from htp.bindings import nvgpu_cuda_adapter
from htp.bindings.validate import load_manifest


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


def test_nvgpu_cuda_adapter_builds_ptx_and_cubin(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")
    manifest = load_manifest(package_dir)

    monkeypatch.setattr(nvgpu_cuda_adapter, "_find_nvcc", lambda: "/usr/local/cuda/bin/nvcc")

    def fake_run_nvcc(
        nvcc_path: str,
        source_path: Path,
        output_path: Path,
        cuda_arch: str,
        *,
        target_format: str,
        extra_flags=(),
    ) -> None:
        assert nvcc_path.endswith("nvcc")
        assert source_path.name == "gemm_tile.cu"
        assert cuda_arch == "sm_80"
        assert target_format in {"ptx", "cubin"}
        assert "--generate-line-info" in extra_flags
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(target_format.encode())

    monkeypatch.setattr(nvgpu_cuda_adapter, "_run_nvcc", fake_run_nvcc)

    built_outputs, diagnostics, trace_ref = nvgpu_cuda_adapter.build_package(
        package_dir, manifest, force=True
    )

    assert diagnostics == []
    assert built_outputs == ["build/nvgpu/gemm_tile.ptx", "build/nvgpu/gemm_tile.cubin"]
    assert (package_dir / "build" / "nvgpu" / "gemm_tile.ptx").read_bytes() == b"ptx"
    assert (package_dir / "build" / "nvgpu" / "gemm_tile.cubin").read_bytes() == b"cubin"
    assert trace_ref is not None
    assert (package_dir / trace_ref).is_file()


def test_nvgpu_cuda_adapter_runs_kernel_with_tensor_arguments(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")
    manifest = load_manifest(package_dir)
    build_dir = package_dir / "build" / "nvgpu"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "gemm_tile.ptx").write_bytes(b"ptx")
    (build_dir / "gemm_tile.cubin").write_bytes(b"cubin")

    calls: list[dict[str, object]] = []

    def fake_run_with_cuda_driver(contract, kernel, args):
        calls.append(
            {
                "entry": contract.entrypoint,
                "kernel": kernel.func_id,
                "param_names": [param.name for param in kernel.params],
                "launch_kind": kernel.launch.kind,
                "thread_block": kernel.thread_block,
                "args": args,
            }
        )
        return {
            "adapter": "cuda_driver",
            "entry": contract.entrypoint,
            "kernel": kernel.func_id,
            "cubin": (package_dir / "build" / "nvgpu" / "gemm_tile.cubin").as_posix(),
            "thread_block": list(kernel.thread_block),
            "grid": [1, 1, 1],
            "params": [param.name for param in kernel.params],
            "profile_plan": kernel.profile_plan,
        }

    monkeypatch.setattr(nvgpu_cuda_adapter, "_run_with_cuda_driver", fake_run_with_cuda_driver)
    monkeypatch.setattr(nvgpu_cuda_adapter, "_find_nvcc", lambda: "/usr/local/cuda/bin/nvcc")

    a = np.ones((4, 4), dtype=np.float32)
    b = np.ones((4, 4), dtype=np.float32)
    c = np.zeros((4, 4), dtype=np.float32)
    ok, result, diagnostics, trace_ref = nvgpu_cuda_adapter.run_package(
        package_dir,
        manifest,
        entry="gemm_tile",
        args=(a, b, c, 4, 4, 4),
        kwargs=None,
    )

    assert ok is True
    assert diagnostics == []
    assert result["adapter"] == "cuda_driver"
    assert result["entry"] == "gemm_tile"
    assert result["kernel"] == "gemm_tile_kernel0"
    assert result["cubin"] == (package_dir / "build" / "nvgpu" / "gemm_tile.cubin").as_posix()
    assert result["thread_block"] == [16, 16, 1]
    assert result["grid"] == [1, 1, 1]
    assert result["params"] == ["A", "B", "C", "M", "N", "K"]
    assert result["profile_plan"] == {
        "profile": "ampere",
        "matrix_engine": "mma_sync",
        "async_loader": "cp_async",
        "pipeline_stages": 2,
        "cluster_shape": [1, 1, 1],
    }
    assert isinstance(result["runtime_ms"], float)
    assert result["perf_ref"] == "metrics/perf.json"
    assert result["trace_ref"] == trace_ref
    assert trace_ref is not None
    assert (package_dir / trace_ref).is_file()
    perf_payload = json.loads((package_dir / "metrics" / "perf.json").read_text())
    assert perf_payload["schema"] == "htp.perf.v1"
    assert perf_payload["backend"] == "nvgpu"
    assert perf_payload["entry"] == "gemm_tile"
    assert perf_payload["profile_plan"]["profile"] == "ampere"
    assert calls == [
        {
            "entry": "gemm_tile",
            "kernel": "gemm_tile_kernel0",
            "param_names": ["A", "B", "C", "M", "N", "K"],
            "launch_kind": "grid_2d",
            "thread_block": (16, 16, 1),
            "args": (a, b, c, 4, 4, 4),
        }
    ]


def test_nvgpu_cuda_adapter_reports_missing_nvcc(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")
    manifest = load_manifest(package_dir)
    monkeypatch.setattr(nvgpu_cuda_adapter, "_find_nvcc", lambda: None)

    built_outputs, diagnostics, trace_ref = nvgpu_cuda_adapter.build_package(
        package_dir, manifest, force=True
    )

    assert built_outputs == []
    assert diagnostics == [
        {
            "code": "HTP.BINDINGS.NVGPU_COMPILER_UNAVAILABLE",
            "detail": "nvcc was not found in PATH; install the CUDA toolkit or use sim replay.",
            "expected_compiler": "nvcc",
        }
    ]
    assert trace_ref is not None


def test_nvgpu_cuda_adapter_normalizes_cuda_arch_flag():
    assert nvgpu_cuda_adapter._normalize_cuda_arch("sm80") == "sm_80"
    assert nvgpu_cuda_adapter._normalize_cuda_arch("sm_80") == "sm_80"


def test_nvgpu_cuda_adapter_rebuilds_when_cuda_source_changes(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program=_gemm_program(), profile="ampere")
    manifest = load_manifest(package_dir)

    monkeypatch.setattr(nvgpu_cuda_adapter, "_find_nvcc", lambda: "/usr/local/cuda/bin/nvcc")

    def fake_run_nvcc(
        nvcc_path: str,
        source_path: Path,
        output_path: Path,
        cuda_arch: str,
        *,
        target_format: str,
        extra_flags=(),
    ) -> None:
        del nvcc_path, source_path, cuda_arch, target_format, extra_flags
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(str(time.time()).encode())

    monkeypatch.setattr(nvgpu_cuda_adapter, "_run_nvcc", fake_run_nvcc)

    built_outputs, diagnostics, _trace_ref = nvgpu_cuda_adapter.build_package(
        package_dir, manifest, force=True
    )
    assert diagnostics == []
    cubin_path = package_dir / built_outputs[-1]
    initial_mtime = cubin_path.stat().st_mtime

    time.sleep(0.02)
    kernel_source_path = package_dir / "codegen" / "nvgpu" / "kernels" / "gemm_tile.cu"
    kernel_source_path.write_text(kernel_source_path.read_text() + "\n// rebuild marker\n")

    rebuilt_outputs, rebuild_diagnostics, _rebuild_trace_ref = nvgpu_cuda_adapter.build_package(
        package_dir, manifest, force=False
    )

    assert rebuild_diagnostics == []
    assert rebuilt_outputs == built_outputs
    assert cubin_path.stat().st_mtime > initial_mtime
