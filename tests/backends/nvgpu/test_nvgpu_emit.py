import json
from pathlib import Path

from htp.bindings.api import bind
from htp.backends.nvgpu.emit import emit_package


def test_nvgpu_emit_prefers_cu_source_artifacts(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    manifest = emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["load", "mma", "store"],
        },
        profile="ampere",
    )

    kernel_source = package_dir / "codegen" / "nvgpu" / "kernels" / "demo_kernel.cu"
    host_source = package_dir / "codegen" / "nvgpu" / "host" / "demo_kernel_launch.py"
    codegen_index_path = package_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json"
    toolchain_manifest_path = package_dir / "build" / "toolchain.json"

    assert manifest == json.loads((package_dir / "manifest.json").read_text())
    assert manifest["target"] == {
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:ampere:sm80",
    }
    assert manifest["outputs"] == {
        "nvgpu_codegen_index": "codegen/nvgpu/nvgpu_codegen.json",
        "toolchain_manifest": "build/toolchain.json",
    }
    assert manifest["extensions"]["nvgpu"] == {
        "kernel_project_dir": "codegen/nvgpu",
        "launch_entry": {
            "source": "host/demo_kernel_launch.py",
            "function_name": "launch_demo_kernel",
        },
        "cuda_runtime_contract": "cuda-runtime:stub",
        "codegen_mode": "cuda_source",
        "toolchain_manifest": "build/toolchain.json",
    }

    assert kernel_source.is_file()
    assert host_source.is_file()
    assert codegen_index_path.is_file()
    assert toolchain_manifest_path.is_file()
    assert list((package_dir / "codegen" / "nvgpu" / "kernels").glob("*.ptx")) == []
    assert list((package_dir / "codegen" / "nvgpu" / "kernels").glob("*.cubin")) == []

    codegen_index = json.loads(codegen_index_path.read_text())
    assert codegen_index == {
        "schema": "htp.nvgpu.codegen.v1",
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:ampere:sm80",
        "entrypoint": "demo_kernel",
        "launch": {
            "source": "codegen/nvgpu/host/demo_kernel_launch.py",
            "function_name": "launch_demo_kernel",
        },
        "kernels": [
            {
                "kernel_id": "demo_kernel.kernel0",
                "func_id": "demo_kernel_kernel0",
                "source": "codegen/nvgpu/kernels/demo_kernel.cu",
                "thread_block": [128, 1, 1],
                "shared_memory_bytes": 0,
                "capabilities": ["cp.async", "mma.sync"],
            }
        ],
    }
    assert json.loads(toolchain_manifest_path.read_text()) == {
        "schema": "htp.nvgpu.toolchain.v1",
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:ampere:sm80",
        "codegen_mode": "cuda_source",
        "cuda_runtime_contract": "cuda-runtime:stub",
        "cuda_arches": ["sm80"],
        "derived_outputs": [
            "build/nvgpu/demo_kernel.ptx",
            "build/nvgpu/demo_kernel.cubin",
        ],
    }

    report = bind(package_dir).validate()
    assert report.ok is True
    assert report.backend == "nvgpu"
    assert report.variant == "cuda"
    assert report.missing_files == []
    assert report.diagnostics == []


def test_nvgpu_emit_preserves_existing_manifest_target_metadata(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "target": {
                    "existing_target": "keep-me",
                    "hardware_profile": "stale-profile",
                }
            },
            indent=2,
        )
        + "\n"
    )

    manifest = emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["mma"],
        },
        profile="blackwell",
    )

    assert manifest["target"] == {
        "existing_target": "keep-me",
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:blackwell:sm100",
    }
