from __future__ import annotations

from pathlib import Path

from htp.backends.nvgpu.emit import emit_package
from htp.bindings import nvgpu_cuda_adapter
from htp.bindings.validate import load_manifest


def test_nvgpu_cuda_adapter_builds_ptx_and_cubin(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={"entry": "demo_kernel", "ops": ["mma"]},
        profile="ampere",
    )
    manifest = load_manifest(package_dir)

    monkeypatch.setattr(nvgpu_cuda_adapter, "_find_nvcc", lambda: "/usr/local/cuda/bin/nvcc")

    def fake_run_nvcc(
        nvcc_path: str, source_path: Path, output_path: Path, cuda_arch: str, *, target_format: str
    ) -> None:
        assert nvcc_path.endswith("nvcc")
        assert source_path.name == "demo_kernel.cu"
        assert cuda_arch == "sm80"
        assert target_format in {"ptx", "cubin"}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(target_format.encode())

    monkeypatch.setattr(nvgpu_cuda_adapter, "_run_nvcc", fake_run_nvcc)

    built_outputs, diagnostics = nvgpu_cuda_adapter.build_package(
        package_dir,
        manifest,
        force=True,
    )

    assert diagnostics == []
    assert built_outputs == [
        "build/nvgpu/demo_kernel.ptx",
        "build/nvgpu/demo_kernel.cubin",
    ]
    assert (package_dir / "build" / "nvgpu" / "demo_kernel.ptx").read_bytes() == b"ptx"
    assert (package_dir / "build" / "nvgpu" / "demo_kernel.cubin").read_bytes() == b"cubin"


def test_nvgpu_cuda_adapter_runs_cubin_with_driver(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={"entry": "demo_kernel", "ops": ["mma"]},
        profile="ampere",
    )
    manifest = load_manifest(package_dir)
    build_dir = package_dir / "build" / "nvgpu"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "demo_kernel.ptx").write_bytes(b"ptx")
    (build_dir / "demo_kernel.cubin").write_bytes(b"cubin")

    calls: list[tuple[str, str, tuple[int, int, int]]] = []

    monkeypatch.setattr(
        nvgpu_cuda_adapter,
        "_launch_with_cuda_driver",
        lambda *, cubin_path, kernel_name, thread_block: calls.append(
            (cubin_path.as_posix(), kernel_name, thread_block)
        ),
    )
    monkeypatch.setattr(nvgpu_cuda_adapter, "_find_nvcc", lambda: "/usr/local/cuda/bin/nvcc")

    ok, result, diagnostics = nvgpu_cuda_adapter.run_package(
        package_dir,
        manifest,
        entry="demo_kernel",
        args=(),
        kwargs=None,
    )

    assert ok is True
    assert diagnostics == []
    assert result == {
        "adapter": "cuda_driver",
        "entry": "demo_kernel",
        "kernel": "demo_kernel_kernel0",
        "cubin": (package_dir / "build" / "nvgpu" / "demo_kernel.cubin").as_posix(),
        "thread_block": [128, 1, 1],
    }
    assert calls == [
        (
            (package_dir / "build" / "nvgpu" / "demo_kernel.cubin").as_posix(),
            "demo_kernel_kernel0",
            (128, 1, 1),
        )
    ]


def test_nvgpu_cuda_adapter_reports_missing_nvcc(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={"entry": "demo_kernel", "ops": ["mma"]},
        profile="ampere",
    )
    manifest = load_manifest(package_dir)
    monkeypatch.setattr(nvgpu_cuda_adapter, "_find_nvcc", lambda: None)

    built_outputs, diagnostics = nvgpu_cuda_adapter.build_package(
        package_dir,
        manifest,
        force=True,
    )

    assert built_outputs == []
    assert diagnostics == [
        {
            "code": "HTP.BINDINGS.NVGPU_COMPILER_UNAVAILABLE",
            "detail": "nvcc was not found in PATH; install the CUDA toolkit or use sim replay.",
            "expected_compiler": "nvcc",
        }
    ]
