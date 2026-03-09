import json

from htp import ark, compile_program
from htp.backends.nvgpu.emit import emit_package
from htp.bindings.api import bind


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
        "cuda_runtime_contract": "cuda-runtime:driver",
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
                "thread_block": [16, 16, 1],
                "shared_memory_bytes": 0,
                "capabilities": ["cp.async", "ldmatrix", "mma.sync"],
                "params": [
                    {"name": "A", "kind": "buffer", "dtype": "f32", "role": "input", "shape": ["M", "K"]},
                    {"name": "B", "kind": "buffer", "dtype": "f32", "role": "input", "shape": ["K", "N"]},
                    {"name": "C", "kind": "buffer", "dtype": "f32", "role": "output", "shape": ["M", "N"]},
                    {"name": "M", "kind": "scalar", "dtype": "i32", "role": "shape", "shape": []},
                    {"name": "N", "kind": "scalar", "dtype": "i32", "role": "shape", "shape": []},
                    {"name": "K", "kind": "scalar", "dtype": "i32", "role": "shape", "shape": []},
                ],
                "launch": {"kind": "grid_2d", "extents": ["M", "N"]},
                "op": "matmul",
                "attrs": {"dtype": "f32", "m": "M", "n": "N", "k": "K"},
            }
        ],
    }
    assert json.loads(toolchain_manifest_path.read_text()) == {
        "schema": "htp.nvgpu.toolchain.v1",
        "backend": "nvgpu",
        "variant": "cuda",
        "hardware_profile": "nvidia:ampere:sm80",
        "codegen_mode": "cuda_source",
        "cuda_runtime_contract": "cuda-runtime:driver",
        "cuda_arches": ["sm80"],
        "derived_outputs": [
            "build/nvgpu/demo_kernel.ptx",
            "build/nvgpu/demo_kernel.cubin",
        ],
    }
    assert "const int row = blockIdx.y * blockDim.y + threadIdx.y;" in kernel_source.read_text()
    assert (
        'def launch_demo_kernel(A, B, C, M, N, K, mode="sim", trace=None, runtime=None):'
        in host_source.read_text()
    )

    report = bind(package_dir).validate()
    assert report.ok is True
    assert report.backend == "nvgpu"
    assert report.variant == "cuda"
    assert report.missing_files == []
    assert report.diagnostics == []


def test_nvgpu_codegen_records_arknife_hardware_and_instruction_plan(tmp_path):
    @ark.build(target="nvgpu-blackwell", hardware=ark.blackwell())
    def blackwell_mainloop():
        A = ark.tensor("A", dtype="bf16", shape=("M", "K"), role="input", memory="global")
        B = ark.tensor("B", dtype="bf16", shape=("K", "N"), role="input", memory="global")
        C = ark.tensor("C", dtype="f32", shape=("M", "N"), role="output", memory="global")
        AS = ark.tensor("AS", dtype="bf16", shape=("BM", "BK"), memory="shared")
        BS = ark.tensor("BS", dtype="bf16", shape=("BK", "BN"), memory="shared")
        TC = ark.tensor("TC", dtype="f32", shape=("BM", "BN"), memory="tensor")
        with ark.spatial("cluster", ark.axis("cluster_m", 2), ark.axis("cluster_n", 1)):
            with ark.pipeline(ark.axis("k_outer", 2), stages=2):
                ark.tma_load(AS, A, channel="cluster_pipe")
                ark.tma_load(BS, B, channel="cluster_pipe")
                ark.wgmma(TC, AS, BS, accum=TC, shape=(64, 128, 16), channel="cluster_pipe")
            ark.tma_store(C, TC, channel="store_pipe")
        return A, B, C

    compiled = compile_program(
        package_dir=tmp_path / "blackwell_ark",
        target="nvgpu-blackwell",
        program=blackwell_mainloop,
    )

    codegen = json.loads((compiled.package_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json").read_text())
    kernel = codegen["kernels"][0]
    assert codegen["hardware_profile"] == "nvidia:blackwell:sm100"
    assert codegen["arknife"]["hardware"]["parallelism_levels"] == [
        "lane",
        "warp",
        "warpgroup",
        "block",
        "cluster",
        "grid",
    ]
    assert codegen["arknife"]["channels"][0]["name"] == "cluster_pipe"
    assert [item["instruction"] for item in kernel["instruction_plan"]] == [
        "tma_load",
        "tma_load",
        "wgmma",
        "tma_store",
    ]
    assert (
        "wgmma"
        in (compiled.package_dir / "codegen" / "nvgpu" / "kernels" / "blackwell_mainloop.cu").read_text()
    )


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


def test_bind_prefers_nvgpu_binding_when_backend_is_missing(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["mma"],
        },
        profile="ampere",
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["target"]["backend"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    binding = bind(package_dir)
    report = binding.validate()

    assert binding.__class__.__name__ == "NVGPUBinding"
    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
            "detail": "Manifest target.backend does not match NV-GPU binding selection.",
            "field": "backend",
            "manifest_field": "target.backend",
            "manifest_value": None,
            "expected_value": "nvgpu",
        }
    ]


def test_bind_prefers_nvgpu_binding_over_shared_toolchain_marker(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["mma"],
        },
        profile="ampere",
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["target"]["backend"]
    manifest.pop("outputs")
    manifest["extensions"] = {}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    binding = bind(package_dir)
    report = binding.validate()

    assert binding.__class__.__name__ == "NVGPUBinding"
    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.NVGPU_MISSING_METADATA",
            "detail": "manifest.json outputs.nvgpu_codegen_index is required for NV-GPU packages.",
            "manifest_field": "outputs.nvgpu_codegen_index",
        },
        {
            "code": "HTP.BINDINGS.NVGPU_MISSING_METADATA",
            "detail": "manifest.json outputs.toolchain_manifest is required for NV-GPU packages.",
            "manifest_field": "outputs.toolchain_manifest",
        },
        {
            "code": "HTP.BINDINGS.NVGPU_MISSING_METADATA",
            "detail": "manifest.json extensions.nvgpu is required for NV-GPU packages.",
            "manifest_field": "extensions.nvgpu",
        },
        {
            "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
            "detail": "Manifest target.backend does not match NV-GPU binding selection.",
            "field": "backend",
            "manifest_field": "target.backend",
            "manifest_value": None,
            "expected_value": "nvgpu",
        },
    ]


def test_nvgpu_binding_validates_launch_entry_parity(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["mma"],
        },
        profile="ampere",
    )

    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["extensions"]["nvgpu"]["launch_entry"]["source"] = "host/wrong_launch.py"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    report = bind(package_dir).validate()

    assert report.ok is False
    assert report.diagnostics == [
        {
            "code": "HTP.BINDINGS.NVGPU_METADATA_MISMATCH",
            "detail": "manifest.json extensions.nvgpu.launch_entry.source does not match nvgpu_codegen.json launch.source after project-relative normalization.",
            "manifest_field": "extensions.nvgpu.launch_entry.source",
            "manifest_value": "host/wrong_launch.py",
            "codegen_field": "codegen/nvgpu/nvgpu_codegen.json.launch.source",
            "codegen_value": "codegen/nvgpu/host/demo_kernel_launch.py",
        }
    ]
