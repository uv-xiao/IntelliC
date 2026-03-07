from __future__ import annotations

import shutil
import time
from pathlib import Path

from htp.backends.pto.emit import emit_package
from htp.bindings import pto_runtime_adapter
from htp.bindings.validate import load_manifest


class _FakeKernelCompiler:
    def __init__(self) -> None:
        self.gxx15 = type("FakeGxx15", (), {"cxx_path": "g++-15"})()

    def compile_orchestration(self, runtime_name: str, source_path: str, extra_include_dirs=None) -> bytes:
        assert runtime_name == "host_build_graph"
        assert Path(source_path).name == "demo_kernel_orchestration.cpp"
        assert extra_include_dirs is not None
        return b"orch-binary"

    def compile_incore(
        self,
        source_path: str,
        core_type: str = "aiv",
        pto_isa_root: str | None = None,
        extra_include_dirs=None,
    ) -> bytes:
        assert Path(source_path).name == "demo_kernel.cpp"
        assert core_type == "aiv"
        assert extra_include_dirs is not None
        assert pto_isa_root is None
        return b"kernel-binary"


class _FakeRuntimeBuilder:
    def __init__(self, platform: str) -> None:
        assert platform == "a2a3sim"

    def build(self, runtime_name: str):
        assert runtime_name == "host_build_graph"
        return (b"host-runtime", b"aicpu-runtime", b"aicore-runtime")

    def get_kernel_compiler(self) -> _FakeKernelCompiler:
        return _FakeKernelCompiler()


class _FakeBindingsModule:
    ARG_SCALAR = 0

    @staticmethod
    def bind_host_binary(binary: bytes):
        assert binary == b"host-runtime"

        class _Runtime:
            def initialize(
                self,
                orch_so_binary,
                orch_func_name,
                func_args=None,
                arg_types=None,
                arg_sizes=None,
                kernel_binaries=None,
            ):
                assert orch_so_binary == b"orch-binary"
                assert orch_func_name == "demo_kernel_orchestrate"
                assert func_args == [7]
                assert arg_types == [0]
                assert arg_sizes == [0]
                assert kernel_binaries == [(0, b"kernel-binary")]

            def finalize(self):
                return None

        return _Runtime

    @staticmethod
    def set_device(device_id: int) -> None:
        assert device_id == 0

    @staticmethod
    def launch_runtime(runtime, aicpu_thread_num, block_dim, device_id, aicpu_binary, aicore_binary) -> None:
        assert aicpu_thread_num == 1
        assert block_dim == 1
        assert device_id == 0
        assert aicpu_binary == b"aicpu-runtime"
        assert aicore_binary == b"aicore-runtime"


def test_pto_runtime_adapter_builds_expected_outputs(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program={"entry": "demo_kernel", "ops": ["compute_tile"]})
    manifest = load_manifest(package_dir)

    monkeypatch.setattr(
        pto_runtime_adapter,
        "_load_reference_modules",
        lambda: (
            type("RuntimeBuilderModule", (), {"RuntimeBuilder": _FakeRuntimeBuilder}),
            _FakeBindingsModule,
        ),
    )

    built_outputs, diagnostics = pto_runtime_adapter.build_package(
        package_dir,
        manifest,
        mode="sim",
        force=True,
    )

    assert diagnostics == []
    assert built_outputs == [
        "build/pto/runtime/libhost_runtime.so",
        "build/pto/runtime/libaicpu_runtime.so",
        "build/pto/runtime/aicore_runtime.bin",
        "build/pto/orchestration/demo_kernel_orchestration.so",
        "build/pto/kernels/0.bin",
    ]
    for relpath in built_outputs:
        assert (package_dir / relpath).is_file()


def test_pto_runtime_adapter_runs_built_package(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program={"entry": "demo_kernel", "ops": ["compute_tile"]})
    manifest = load_manifest(package_dir)

    monkeypatch.setattr(
        pto_runtime_adapter,
        "_load_reference_modules",
        lambda: (
            type("RuntimeBuilderModule", (), {"RuntimeBuilder": _FakeRuntimeBuilder}),
            _FakeBindingsModule,
        ),
    )

    ok, result, diagnostics = pto_runtime_adapter.run_package(
        package_dir,
        manifest,
        mode="sim",
        entry="demo_kernel",
        args=(7,),
        kwargs=None,
    )

    assert ok is True
    assert diagnostics == []
    assert result == {
        "adapter": "pto-runtime",
        "entry": "demo_kernel",
        "platform": "a2a3sim",
        "runtime_name": "host_build_graph",
        "built_outputs": [
            "build/pto/runtime/libhost_runtime.so",
            "build/pto/runtime/libaicpu_runtime.so",
            "build/pto/runtime/aicore_runtime.bin",
            "build/pto/orchestration/demo_kernel_orchestration.so",
            "build/pto/kernels/0.bin",
        ],
    }


def test_pto_runtime_adapter_reports_missing_reference_runtime(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program={"entry": "demo_kernel", "ops": ["compute_tile"]})
    manifest = load_manifest(package_dir)

    monkeypatch.setattr(
        pto_runtime_adapter,
        "_load_reference_modules",
        lambda: (_ for _ in ()).throw(FileNotFoundError("missing reference runtime")),
    )

    built_outputs, diagnostics = pto_runtime_adapter.build_package(
        package_dir,
        manifest,
        mode="sim",
        force=True,
    )

    assert built_outputs == []
    assert diagnostics == [
        {
            "code": "HTP.BINDINGS.PTO_REFERENCE_UNAVAILABLE",
            "detail": "missing reference runtime",
        }
    ]


def test_pto_runtime_adapter_prefers_available_host_gxx_for_sim(monkeypatch):
    compiler = _FakeKernelCompiler()
    monkeypatch.setattr(shutil, "which", lambda name: "/bin/g++" if name == "g++" else None)

    pto_runtime_adapter._configure_sim_kernel_compiler(compiler, "a2a3sim")

    assert compiler.gxx15.cxx_path == "/bin/g++"


def test_pto_runtime_adapter_rebuilds_when_codegen_sources_change(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(package_dir, program={"entry": "demo_kernel", "ops": ["compute_tile"]})
    manifest = load_manifest(package_dir)

    monkeypatch.setattr(
        pto_runtime_adapter,
        "_load_reference_modules",
        lambda: (
            type("RuntimeBuilderModule", (), {"RuntimeBuilder": _FakeRuntimeBuilder}),
            _FakeBindingsModule,
        ),
    )

    built_outputs, diagnostics = pto_runtime_adapter.build_package(
        package_dir,
        manifest,
        mode="sim",
        force=True,
    )
    assert diagnostics == []
    kernel_output_path = package_dir / built_outputs[-1]
    initial_mtime = kernel_output_path.stat().st_mtime

    time.sleep(0.02)
    kernel_source_path = package_dir / "codegen" / "pto" / "kernels" / "aiv" / "demo_kernel.cpp"
    kernel_source_path.write_text(kernel_source_path.read_text() + "\n// rebuild marker\n")

    rebuilt_outputs, rebuild_diagnostics = pto_runtime_adapter.build_package(
        package_dir,
        manifest,
        mode="sim",
        force=False,
    )

    assert rebuild_diagnostics == []
    assert rebuilt_outputs == built_outputs
    assert kernel_output_path.stat().st_mtime > initial_mtime


def test_pto_runtime_adapter_prefers_3rdparty_runtime_dir(monkeypatch, tmp_path):
    thirdparty_dir = tmp_path / "3rdparty" / "pto-runtime" / "python"
    references_dir = tmp_path / "references" / "pto-runtime" / "python"
    thirdparty_dir.mkdir(parents=True)
    references_dir.mkdir(parents=True)
    monkeypatch.setattr(pto_runtime_adapter, "REPO_ROOT", tmp_path)

    assert pto_runtime_adapter._resolve_reference_python_dir() == thirdparty_dir


def test_pto_runtime_adapter_falls_back_to_references_runtime_dir(monkeypatch, tmp_path):
    references_dir = tmp_path / "references" / "pto-runtime" / "python"
    references_dir.mkdir(parents=True)
    monkeypatch.setattr(pto_runtime_adapter, "REPO_ROOT", tmp_path)

    assert pto_runtime_adapter._resolve_reference_python_dir() == references_dir
