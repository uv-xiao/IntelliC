import htp.runtime as runtime_api
from htp.backends.nvgpu.emit import emit_package
from htp.bindings.api import bind


def test_nvgpu_build_reports_source_and_derived_outputs(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["load", "mma", "store"],
        },
        profile="ampere",
    )

    result = bind(package_dir).build(mode="sim")

    assert result.ok is True
    assert result.mode == "sim"
    assert result.built_outputs == [
        "codegen/nvgpu/nvgpu_codegen.json",
        "build/toolchain.json",
        "codegen/nvgpu/host/demo_kernel_launch.py",
        "codegen/nvgpu/kernels/demo_kernel.cu",
        "build/nvgpu/demo_kernel.ptx",
        "build/nvgpu/demo_kernel.cubin",
    ]
    assert len(result.log_paths) == 1
    assert result.diagnostics == []


def test_nvgpu_run_uses_launch_entry_and_runtime(tmp_path, monkeypatch):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["load", "mma", "store"],
        },
        profile="ampere",
    )

    runtime = runtime_api.Runtime()
    runtime.register_kernel(
        "demo_kernel.kernel0",
        lambda *, args, mode, artifacts, trace=None: {
            "args": args,
            "mode": mode,
            "artifacts": dict(artifacts),
            "trace": trace,
        },
    )
    monkeypatch.setattr(runtime_api, "default_runtime", lambda: runtime)

    session = bind(package_dir).load(mode="sim")
    result = session.run("demo_kernel", args=(1, 2), trace="basic")

    assert result.ok is True
    assert result.mode == "sim"
    assert result.entry == "launch_demo_kernel"
    assert result.result == {
        "args": (1, 2),
        "mode": "sim",
        "artifacts": {
            "backend": "nvgpu",
            "variant": "cuda",
            "hardware_profile": "nvidia:ampere:sm80",
            "kernel_source": "codegen/nvgpu/kernels/demo_kernel.cu",
        },
        "trace": "basic",
    }
    assert result.diagnostics == []
    assert result.log_path is not None
