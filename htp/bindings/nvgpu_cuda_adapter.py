from __future__ import annotations

import ctypes
import ctypes.util
import json
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NVGPUKernelContract:
    kernel_id: str
    func_id: str
    source: str
    thread_block: tuple[int, int, int]


@dataclass(frozen=True)
class NVGPUContract:
    package_dir: Path
    entrypoint: str
    hardware_profile: str
    cuda_arch: str
    kernels: tuple[NVGPUKernelContract, ...]
    derived_outputs: tuple[str, ...]


def build_package(
    package_dir: Path,
    manifest: Mapping[str, Any],
    *,
    force: bool = False,
) -> tuple[list[str], list[dict[str, Any]]]:
    contract = load_contract(package_dir, manifest)
    nvcc_path = _find_nvcc()
    if nvcc_path is None:
        return [], [
            {
                "code": "HTP.BINDINGS.NVGPU_COMPILER_UNAVAILABLE",
                "detail": "nvcc was not found in PATH; install the CUDA toolkit or use sim replay.",
                "expected_compiler": "nvcc",
            }
        ]

    built_outputs = list(contract.derived_outputs)
    if not force and all((package_dir / relpath).exists() for relpath in built_outputs):
        return built_outputs, []

    try:
        for kernel in contract.kernels:
            source_path = package_dir / kernel.source
            ptx_path = package_dir / f"build/nvgpu/{Path(kernel.source).stem}.ptx"
            cubin_path = package_dir / f"build/nvgpu/{Path(kernel.source).stem}.cubin"
            ptx_path.parent.mkdir(parents=True, exist_ok=True)
            _run_nvcc(nvcc_path, source_path, ptx_path, contract.cuda_arch, target_format="ptx")
            _run_nvcc(nvcc_path, source_path, cubin_path, contract.cuda_arch, target_format="cubin")
    except Exception as exc:
        return [], [
            {
                "code": "HTP.BINDINGS.NVGPU_BUILD_ERROR",
                "detail": str(exc),
                "cuda_arch": contract.cuda_arch,
            }
        ]
    return built_outputs, []


def run_package(
    package_dir: Path,
    manifest: Mapping[str, Any],
    *,
    entry: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any] | None,
) -> tuple[bool, Any, list[dict[str, Any]]]:
    contract = load_contract(package_dir, manifest)
    if kwargs:
        return False, None, [
            {
                "code": "HTP.BINDINGS.NVGPU_UNSUPPORTED_KEYWORD_ARGS",
                "detail": "NV-GPU device execution only supports positional arguments in v1.",
            }
        ]
    if args:
        return False, None, [
            {
                "code": "HTP.BINDINGS.NVGPU_UNSUPPORTED_ARGUMENTS",
                "detail": "NV-GPU device execution only supports zero-argument kernels in v1.",
            }
        ]
    if entry != contract.entrypoint:
        return False, None, [
            {
                "code": "HTP.BINDINGS.MISSING_ENTRYPOINT",
                "detail": f"Entrypoint {entry!r} is not defined for the NV-GPU package.",
                "entry": entry,
                "available_entries": [contract.entrypoint],
            }
        ]

    built_outputs, build_diagnostics = build_package(package_dir, manifest, force=False)
    if build_diagnostics:
        return False, None, build_diagnostics

    kernel = contract.kernels[0]
    cubin_path = package_dir / f"build/nvgpu/{Path(kernel.source).stem}.cubin"
    try:
        _launch_with_cuda_driver(
            cubin_path=cubin_path,
            kernel_name=kernel.func_id,
            thread_block=kernel.thread_block,
        )
    except Exception as exc:
        return False, None, [
            {
                "code": "HTP.BINDINGS.NVGPU_RUNTIME_UNAVAILABLE",
                "detail": str(exc),
                "kernel": kernel.func_id,
                "cubin": cubin_path.as_posix(),
            }
        ]
    return (
        True,
        {
            "adapter": "cuda_driver",
            "entry": contract.entrypoint,
            "kernel": kernel.func_id,
            "cubin": cubin_path.as_posix(),
            "thread_block": list(kernel.thread_block),
        },
        [],
    )


def load_contract(package_dir: Path, manifest: Mapping[str, Any]) -> NVGPUContract:
    outputs = manifest.get("outputs")
    codegen_index_path = "codegen/nvgpu/nvgpu_codegen.json"
    toolchain_manifest_path = "build/toolchain.json"
    if isinstance(outputs, Mapping):
        codegen_index_path = str(outputs.get("nvgpu_codegen_index", codegen_index_path))
        toolchain_manifest_path = str(outputs.get("toolchain_manifest", toolchain_manifest_path))

    codegen_index = json.loads((package_dir / codegen_index_path).read_text())
    toolchain_manifest = json.loads((package_dir / toolchain_manifest_path).read_text())
    kernels = tuple(
        NVGPUKernelContract(
            kernel_id=str(kernel["kernel_id"]),
            func_id=str(kernel["func_id"]),
            source=str(kernel["source"]),
            thread_block=tuple(int(value) for value in kernel["thread_block"]),
        )
        for kernel in codegen_index["kernels"]
    )
    cuda_arches = toolchain_manifest.get("cuda_arches")
    if not isinstance(cuda_arches, list) or not cuda_arches or not isinstance(cuda_arches[0], str):
        raise ValueError("build/toolchain.json cuda_arches must contain at least one CUDA architecture.")
    derived_outputs = toolchain_manifest.get("derived_outputs")
    if not isinstance(derived_outputs, list) or not all(isinstance(path, str) for path in derived_outputs):
        raise ValueError("build/toolchain.json derived_outputs must be a list of strings.")
    return NVGPUContract(
        package_dir=package_dir,
        entrypoint=str(codegen_index["entrypoint"]),
        hardware_profile=str(codegen_index["hardware_profile"]),
        cuda_arch=str(cuda_arches[0]),
        kernels=kernels,
        derived_outputs=tuple(derived_outputs),
    )


def _find_nvcc() -> str | None:
    return shutil.which("nvcc")


def _run_nvcc(
    nvcc_path: str,
    source_path: Path,
    output_path: Path,
    cuda_arch: str,
    *,
    target_format: str,
) -> None:
    format_flag = "-ptx" if target_format == "ptx" else "-cubin"
    result = subprocess.run(
        [
            nvcc_path,
            format_flag,
            f"-arch={cuda_arch}",
            "-o",
            str(output_path),
            str(source_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"nvcc failed for {source_path}")


def _launch_with_cuda_driver(
    *,
    cubin_path: Path,
    kernel_name: str,
    thread_block: tuple[int, int, int],
) -> None:
    library_path = ctypes.util.find_library("cuda")
    if library_path is None:
        raise RuntimeError("CUDA driver library not found.")
    cuda = ctypes.CDLL(library_path)
    _configure_cuda_driver(cuda)

    context = ctypes.c_void_p()
    module = ctypes.c_void_p()
    function = ctypes.c_void_p()
    device = ctypes.c_int()
    _check_cuda(cuda.cuInit(0), "cuInit")
    _check_cuda(cuda.cuDeviceGet(ctypes.byref(device), 0), "cuDeviceGet")
    _check_cuda(cuda.cuCtxCreate_v2(ctypes.byref(context), 0, device), "cuCtxCreate_v2")
    try:
        _check_cuda(cuda.cuModuleLoad(ctypes.byref(module), str(cubin_path).encode()), "cuModuleLoad")
        _check_cuda(
            cuda.cuModuleGetFunction(ctypes.byref(function), module, kernel_name.encode()),
            "cuModuleGetFunction",
        )
        _check_cuda(
            cuda.cuLaunchKernel(
                function,
                1,
                1,
                1,
                thread_block[0],
                thread_block[1],
                thread_block[2],
                0,
                ctypes.c_void_p(),
                None,
                None,
            ),
            "cuLaunchKernel",
        )
        _check_cuda(cuda.cuCtxSynchronize(), "cuCtxSynchronize")
    finally:
        if module.value:
            cuda.cuModuleUnload(module)
        if context.value:
            cuda.cuCtxDestroy_v2(context)


def _configure_cuda_driver(cuda: ctypes.CDLL) -> None:
    cuda.cuInit.argtypes = [ctypes.c_uint]
    cuda.cuInit.restype = ctypes.c_int
    cuda.cuDeviceGet.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    cuda.cuDeviceGet.restype = ctypes.c_int
    cuda.cuCtxCreate_v2.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint, ctypes.c_int]
    cuda.cuCtxCreate_v2.restype = ctypes.c_int
    cuda.cuCtxDestroy_v2.argtypes = [ctypes.c_void_p]
    cuda.cuCtxDestroy_v2.restype = ctypes.c_int
    cuda.cuModuleLoad.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p]
    cuda.cuModuleLoad.restype = ctypes.c_int
    cuda.cuModuleUnload.argtypes = [ctypes.c_void_p]
    cuda.cuModuleUnload.restype = ctypes.c_int
    cuda.cuModuleGetFunction.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        ctypes.c_char_p,
    ]
    cuda.cuModuleGetFunction.restype = ctypes.c_int
    cuda.cuLaunchKernel.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    cuda.cuLaunchKernel.restype = ctypes.c_int
    cuda.cuCtxSynchronize.argtypes = []
    cuda.cuCtxSynchronize.restype = ctypes.c_int


def _check_cuda(code: int, operation: str) -> None:
    if code != 0:
        raise RuntimeError(f"{operation} failed with CUDA driver error code {code}.")
