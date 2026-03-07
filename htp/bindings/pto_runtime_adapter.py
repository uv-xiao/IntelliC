from __future__ import annotations

import importlib
import importlib.util
import json
import os
import shutil
import sys
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REFERENCE_PYTHON_DIR = Path(__file__).resolve().parents[2] / "references" / "pto-runtime" / "python"


@dataclass(frozen=True)
class PTOContract:
    package_dir: Path
    entrypoint: str
    platform: str
    runtime_name: str
    runtime_config: dict[str, Any]
    orchestration_source: Path
    orchestration_function: str
    kernels: tuple[dict[str, Any], ...]
    toolchain_manifest: dict[str, Any]


def build_package(
    package_dir: Path,
    manifest: Mapping[str, Any],
    *,
    mode: str,
    force: bool = False,
) -> tuple[list[str], list[dict[str, Any]]]:
    contract = load_contract(package_dir, manifest)
    output_paths = _output_paths(contract)
    if (
        not force
        and all((package_dir / relpath).exists() for relpath in output_paths)
        and not _requires_rebuild(contract, output_paths)
    ):
        return output_paths, []

    try:
        runtime_builder_module, bindings_module = _load_reference_modules()
    except Exception as exc:
        return [], [_diagnostic("HTP.BINDINGS.PTO_REFERENCE_UNAVAILABLE", str(exc))]

    try:
        builder = runtime_builder_module.RuntimeBuilder(platform=contract.platform)
        host_runtime, aicpu_runtime, aicore_runtime = builder.build(contract.runtime_name)
        kernel_compiler = builder.get_kernel_compiler()
        _configure_sim_kernel_compiler(kernel_compiler, contract.platform)
        pto_isa_root = _resolve_pto_isa_root(contract)
        orchestration_binary = kernel_compiler.compile_orchestration(
            contract.runtime_name,
            str(contract.orchestration_source),
            extra_include_dirs=[str(contract.package_dir / "codegen" / "pto")],
        )
        kernel_binaries = {}
        for kernel in contract.kernels:
            source_path = _resolve_project_path(contract.package_dir, str(kernel["source"]))
            kernel_binaries[int(kernel["func_id"])] = kernel_compiler.compile_incore(
                str(source_path),
                core_type=str(kernel["core_type"]),
                pto_isa_root=pto_isa_root,
                extra_include_dirs=[str(contract.package_dir / "codegen" / "pto")],
            )
    except Exception as exc:
        return [], [_diagnostic("HTP.BINDINGS.PTO_BUILD_ERROR", str(exc), mode=mode)]

    artifacts = {
        output_paths[0]: host_runtime,
        output_paths[1]: aicpu_runtime,
        output_paths[2]: aicore_runtime,
        output_paths[3]: orchestration_binary,
    }
    for kernel in contract.kernels:
        artifacts[_kernel_output_path(int(kernel["func_id"]))] = kernel_binaries[int(kernel["func_id"])]

    for relpath, payload in artifacts.items():
        output_path = package_dir / relpath
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)

    build_record_path = package_dir / "build" / "pto" / "build_record.json"
    build_record_path.parent.mkdir(parents=True, exist_ok=True)
    build_record_path.write_text(
        json.dumps(
            {
                "platform": contract.platform,
                "runtime_name": contract.runtime_name,
                "kernel_func_ids": [int(kernel["func_id"]) for kernel in contract.kernels],
                "adapter": "pto-runtime",
            },
            indent=2,
        )
        + "\n"
    )
    return output_paths, []


def run_package(
    package_dir: Path,
    manifest: Mapping[str, Any],
    *,
    mode: str,
    entry: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any] | None,
) -> tuple[bool, Any, list[dict[str, Any]]]:
    contract = load_contract(package_dir, manifest)
    if kwargs:
        return (
            False,
            None,
            [
                _diagnostic(
                    "HTP.BINDINGS.PTO_UNSUPPORTED_KEYWORD_ARGS",
                    "PTO package execution only supports positional scalar arguments in v1.",
                )
            ],
        )
    if entry != contract.entrypoint:
        return (
            False,
            None,
            [
                {
                    "code": "HTP.BINDINGS.MISSING_ENTRYPOINT",
                    "detail": f"Entrypoint {entry!r} is not defined for the PTO package.",
                    "entry": entry,
                    "available_entries": [contract.entrypoint],
                }
            ],
        )

    built_outputs, build_diagnostics = build_package(package_dir, manifest, mode=mode, force=False)
    if build_diagnostics:
        return False, None, build_diagnostics

    try:
        _, bindings_module = _load_reference_modules()
    except Exception as exc:
        return False, None, [_diagnostic("HTP.BINDINGS.PTO_REFERENCE_UNAVAILABLE", str(exc))]

    try:
        Runtime = bindings_module.bind_host_binary((package_dir / built_outputs[0]).read_bytes())
        bindings_module.set_device(0)
        runtime = Runtime()
        func_args, arg_types, arg_sizes = _marshal_scalar_args(args, bindings_module)
        kernel_binaries = [
            (int(kernel["func_id"]), (package_dir / _kernel_output_path(int(kernel["func_id"]))).read_bytes())
            for kernel in contract.kernels
        ]
        runtime.initialize(
            (package_dir / built_outputs[3]).read_bytes(),
            contract.orchestration_function,
            func_args=func_args,
            arg_types=arg_types,
            arg_sizes=arg_sizes,
            kernel_binaries=kernel_binaries,
        )
        bindings_module.launch_runtime(
            runtime,
            int(contract.runtime_config["aicpu_thread_num"]),
            int(contract.runtime_config["block_dim"]),
            0,
            (package_dir / built_outputs[1]).read_bytes(),
            (package_dir / built_outputs[2]).read_bytes(),
        )
        runtime.finalize()
    except Exception as exc:
        return False, None, [_diagnostic("HTP.BINDINGS.PTO_RUN_ERROR", str(exc), mode=mode)]

    return (
        True,
        {
            "adapter": "pto-runtime",
            "entry": contract.entrypoint,
            "platform": contract.platform,
            "runtime_name": contract.runtime_name,
            "built_outputs": built_outputs,
        },
        [],
    )


def declared_outputs(package_dir: Path, manifest: Mapping[str, Any]) -> list[str]:
    contract = load_contract(package_dir, manifest)
    return _output_paths(contract)


def load_contract(package_dir: Path, manifest: Mapping[str, Any]) -> PTOContract:
    outputs = manifest.get("outputs")
    output_kernel_config = "codegen/pto/kernel_config.py"
    output_codegen_index = "codegen/pto/pto_codegen.json"
    output_toolchain_manifest = "build/toolchain.json"
    if isinstance(outputs, Mapping):
        output_kernel_config = str(outputs.get("kernel_config", output_kernel_config))
        output_codegen_index = str(outputs.get("pto_codegen_index", output_codegen_index))
        output_toolchain_manifest = str(outputs.get("toolchain_manifest", output_toolchain_manifest))

    kernel_config = _load_python_module(
        package_dir / output_kernel_config, module_name="htp_pto_kernel_config_runtime"
    )
    codegen_index = json.loads((package_dir / output_codegen_index).read_text())
    toolchain_manifest = json.loads((package_dir / output_toolchain_manifest).read_text())
    runtime_config = dict(getattr(kernel_config, "RUNTIME_CONFIG"))
    orchestration = dict(getattr(kernel_config, "ORCHESTRATION"))
    kernels = tuple(dict(kernel) for kernel in getattr(kernel_config, "KERNELS"))
    return PTOContract(
        package_dir=package_dir,
        entrypoint=str(codegen_index["entrypoint"]),
        platform=str(runtime_config.get("platform", manifest.get("target", {}).get("variant", "a2a3sim"))),
        runtime_name=str(runtime_config.get("runtime", "host_build_graph")),
        runtime_config=runtime_config,
        orchestration_source=_resolve_project_path(package_dir, orchestration["source"]),
        orchestration_function=str(orchestration["function_name"]),
        kernels=kernels,
        toolchain_manifest=toolchain_manifest,
    )


def _marshal_scalar_args(
    args: tuple[Any, ...],
    bindings_module: Any,
) -> tuple[list[int] | None, list[int] | None, list[int] | None]:
    if not args:
        return None, None, None
    marshaled: list[int] = []
    for argument in args:
        if isinstance(argument, bool):
            marshaled.append(int(argument))
            continue
        if isinstance(argument, int):
            marshaled.append(argument)
            continue
        raise TypeError(
            "PTO package execution only supports integer-like scalar arguments in v1; "
            f"received {argument.__class__.__name__}."
        )
    arg_types = [bindings_module.ARG_SCALAR for _ in marshaled]
    arg_sizes = [0 for _ in marshaled]
    return marshaled, arg_types, arg_sizes


def _resolve_project_path(package_dir: Path, source: str) -> Path:
    source_path = Path(source)
    if source_path.is_absolute():
        return source_path
    codegen_project_dir = package_dir / "codegen" / "pto"
    return codegen_project_dir / source_path


def _resolve_pto_isa_root(contract: PTOContract) -> str | None:
    if contract.platform == "a2a3sim":
        return None
    env = contract.toolchain_manifest.get("env")
    requested = env.get("PTO_ISA_ROOT") if isinstance(env, Mapping) else None
    if isinstance(requested, str) and requested not in {"", "auto"}:
        return requested
    return os.environ.get("PTO_ISA_ROOT") or os.environ.get("HTP_PTO_ISA_ROOT")


def _configure_sim_kernel_compiler(kernel_compiler: Any, platform: str) -> None:
    if platform != "a2a3sim":
        return
    gxx15 = getattr(kernel_compiler, "gxx15", None)
    if gxx15 is None:
        return
    current_path = getattr(gxx15, "cxx_path", None)
    if not isinstance(current_path, str):
        return
    if shutil.which(current_path) is not None:
        return
    fallback = shutil.which("g++")
    if fallback is not None:
        gxx15.cxx_path = fallback


def _output_paths(contract: PTOContract) -> list[str]:
    outputs = [
        "build/pto/runtime/libhost_runtime.so",
        "build/pto/runtime/libaicpu_runtime.so",
        "build/pto/runtime/aicore_runtime.bin",
        f"build/pto/orchestration/{contract.entrypoint}_orchestration.so",
    ]
    outputs.extend(_kernel_output_path(int(kernel["func_id"])) for kernel in contract.kernels)
    return outputs


def _requires_rebuild(contract: PTOContract, output_paths: list[str]) -> bool:
    newest_input = max(
        path.stat().st_mtime
        for path in (
            contract.package_dir / "manifest.json",
            contract.package_dir / "codegen" / "pto" / "kernel_config.py",
            contract.package_dir / "codegen" / "pto" / "pto_codegen.json",
            contract.package_dir / "build" / "toolchain.json",
            contract.orchestration_source,
            *(
                _resolve_project_path(contract.package_dir, str(kernel["source"]))
                for kernel in contract.kernels
            ),
        )
    )
    oldest_output = min((contract.package_dir / relpath).stat().st_mtime for relpath in output_paths)
    return newest_input > oldest_output


def _kernel_output_path(func_id: int) -> str:
    return f"build/pto/kernels/{func_id}.bin"


def _diagnostic(code: str, detail: str, **payload: Any) -> dict[str, Any]:
    diagnostic = {"code": code, "detail": detail}
    diagnostic.update(payload)
    return diagnostic


@contextmanager
def _reference_python_path():
    if not REFERENCE_PYTHON_DIR.is_dir():
        raise FileNotFoundError(f"Missing PTO reference python directory: {REFERENCE_PYTHON_DIR}")
    sys.path.insert(0, str(REFERENCE_PYTHON_DIR))
    try:
        yield
    finally:
        try:
            sys.path.remove(str(REFERENCE_PYTHON_DIR))
        except ValueError:
            pass


def _load_reference_modules():
    with _reference_python_path():
        runtime_builder_module = importlib.import_module("runtime_builder")
        bindings_module = importlib.import_module("bindings")
    return runtime_builder_module, bindings_module


def _load_python_module(module_path: Path, *, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Python module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
