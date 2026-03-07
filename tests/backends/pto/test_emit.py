import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from htp.backends.pto.emit import emit_package


def _load_module(path: Path):
    spec = spec_from_file_location("kernel_config", path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pto_emit_produces_kernel_config_and_index(tmp_path):
    package_dir = tmp_path / "out"
    package_dir.mkdir()

    manifest = emit_package(
        package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["load_tile", "compute_tile", "store_tile"],
        },
        variant="a2a3sim",
    )

    kernel_config_path = package_dir / "codegen" / "pto" / "kernel_config.py"
    codegen_index_path = package_dir / "codegen" / "pto" / "pto_codegen.json"
    toolchain_manifest_path = package_dir / "build" / "toolchain.json"
    orchestration_source = package_dir / "codegen" / "pto" / "orchestration" / "demo_kernel_orchestration.cpp"
    kernel_source = package_dir / "codegen" / "pto" / "kernels" / "aiv" / "demo_kernel.cpp"

    assert manifest == json.loads((package_dir / "manifest.json").read_text())
    assert manifest["target"] == {
        "backend": "pto",
        "variant": "a2a3sim",
        "hardware_profile": "ascend:a2a3sim",
    }
    assert manifest["outputs"] == {
        "kernel_config": "codegen/pto/kernel_config.py",
        "pto_codegen_index": "codegen/pto/pto_codegen.json",
        "toolchain_manifest": "build/toolchain.json",
    }
    assert manifest["extensions"]["pto"] == {
        "platform": "a2a3sim",
        "kernel_project_dir": "codegen/pto",
        "orchestration_entry": {
            "source": "orchestration/demo_kernel_orchestration.cpp",
            "function_name": "demo_kernel_orchestrate",
        },
        "runtime_config": {
            "aicpu_thread_num": 1,
            "block_dim": 1,
        },
        "pto_runtime_contract": "pto-runtime:dev",
        "pto_isa_contract": "pto-isa:a2a3sim",
        "toolchain_manifest": "build/toolchain.json",
    }

    assert kernel_config_path.is_file()
    assert codegen_index_path.is_file()
    assert toolchain_manifest_path.is_file()
    assert orchestration_source.is_file()
    assert kernel_source.is_file()

    kernel_config = _load_module(kernel_config_path)
    assert kernel_config.KERNELS == [
        {
            "func_id": "demo_kernel_0",
            "source": "kernels/aiv/demo_kernel.cpp",
            "core_type": "aiv",
        }
    ]
    assert kernel_config.ORCHESTRATION == {
        "source": "orchestration/demo_kernel_orchestration.cpp",
        "function_name": "demo_kernel_orchestrate",
    }
    assert kernel_config.RUNTIME_CONFIG == {
        "platform": "a2a3sim",
        "aicpu_thread_num": 1,
        "block_dim": 1,
    }

    assert json.loads(codegen_index_path.read_text()) == {
        "schema": "htp.pto.codegen.v1",
        "backend": "pto",
        "variant": "a2a3sim",
        "entrypoint": "demo_kernel",
        "orchestration": {
            "source": "codegen/pto/orchestration/demo_kernel_orchestration.cpp",
            "function_name": "demo_kernel_orchestrate",
        },
        "kernels": [
            {
                "kernel_id": "demo_kernel.kernel0",
                "func_id": "demo_kernel_0",
                "source": "codegen/pto/kernels/aiv/demo_kernel.cpp",
                "core_type": "aiv",
            }
        ],
    }
    assert json.loads(toolchain_manifest_path.read_text()) == {
        "schema": "htp.pto.toolchain.v1",
        "backend": "pto",
        "variant": "a2a3sim",
        "platform": "a2a3sim",
        "pto_runtime_contract": "pto-runtime:dev",
        "pto_isa_contract": "pto-isa:a2a3sim",
        "compiler_contract": None,
        "env": {
            "PTO_ISA_ROOT": "auto",
        },
        "compile_flags": [],
    }


def test_pto_emit_preserves_existing_manifest_target_metadata(tmp_path):
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
            "ops": ["compute_tile"],
        },
        variant="a2a3",
    )

    assert manifest["target"] == {
        "existing_target": "keep-me",
        "backend": "pto",
        "variant": "a2a3",
        "hardware_profile": "ascend:a2a3",
    }
