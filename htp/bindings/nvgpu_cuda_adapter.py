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

import numpy as np


@dataclass(frozen=True)
class NVGPUParamContract:
    name: str
    kind: str
    dtype: str
    role: str | None
    shape: tuple[str, ...]


@dataclass(frozen=True)
class NVGPULaunchContract:
    kind: str
    extents: tuple[str, ...]


@dataclass(frozen=True)
class NVGPUKernelContract:
    kernel_id: str
    func_id: str
    source: str
    thread_block: tuple[int, int, int]
    params: tuple[NVGPUParamContract, ...]
    launch: NVGPULaunchContract
    op: str
    attrs: dict[str, Any]


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
    if (
        not force
        and all((package_dir / relpath).exists() for relpath in built_outputs)
        and not _requires_rebuild(contract, built_outputs)
    ):
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
        return (
            False,
            None,
            [
                {
                    "code": "HTP.BINDINGS.NVGPU_UNSUPPORTED_KEYWORD_ARGS",
                    "detail": "NV-GPU device execution only supports positional arguments in v1.",
                }
            ],
        )
    if entry != contract.entrypoint:
        return (
            False,
            None,
            [
                {
                    "code": "HTP.BINDINGS.MISSING_ENTRYPOINT",
                    "detail": f"Entrypoint {entry!r} is not defined for the NV-GPU package.",
                    "entry": entry,
                    "available_entries": [contract.entrypoint],
                }
            ],
        )

    built_outputs, build_diagnostics = build_package(package_dir, manifest, force=False)
    if build_diagnostics:
        return False, None, build_diagnostics

    kernel = contract.kernels[0]
    if len(args) != len(kernel.params):
        return (
            False,
            None,
            [
                {
                    "code": "HTP.BINDINGS.NVGPU_ARGUMENT_MISMATCH",
                    "detail": f"Expected {len(kernel.params)} positional arguments, received {len(args)}.",
                    "expected": [param.name for param in kernel.params],
                }
            ],
        )

    try:
        result = _run_with_cuda_driver(contract, kernel, args)
    except Exception as exc:
        return (
            False,
            None,
            [
                {
                    "code": "HTP.BINDINGS.NVGPU_RUNTIME_UNAVAILABLE",
                    "detail": str(exc),
                    "kernel": kernel.func_id,
                    "cubin": (package_dir / f"build/nvgpu/{Path(kernel.source).stem}.cubin").as_posix(),
                }
            ],
        )
    return True, result, []


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
            params=tuple(
                NVGPUParamContract(
                    name=str(param["name"]),
                    kind=str(param["kind"]),
                    dtype=str(param["dtype"]),
                    role=str(param.get("role")) if param.get("role") is not None else None,
                    shape=tuple(str(dim) for dim in param.get("shape", ())),
                )
                for param in kernel.get("params", ())
            ),
            launch=NVGPULaunchContract(
                kind=str(kernel.get("launch", {}).get("kind", "grid_1d")),
                extents=tuple(str(value) for value in kernel.get("launch", {}).get("extents", ())),
            ),
            op=str(kernel.get("op", "elementwise_binary")),
            attrs=dict(kernel.get("attrs", {})),
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
        cuda_arch=_normalize_cuda_arch(str(cuda_arches[0])),
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


def _normalize_cuda_arch(cuda_arch: str) -> str:
    if cuda_arch.startswith("sm_"):
        return cuda_arch
    if cuda_arch.startswith("sm") and len(cuda_arch) > 2:
        return f"sm_{cuda_arch[2:]}"
    return cuda_arch


def _requires_rebuild(contract: NVGPUContract, output_paths: list[str]) -> bool:
    newest_input = max(
        path.stat().st_mtime
        for path in (
            contract.package_dir / "manifest.json",
            contract.package_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json",
            contract.package_dir / "build" / "toolchain.json",
            *(contract.package_dir / kernel.source for kernel in contract.kernels),
        )
    )
    oldest_output = min((contract.package_dir / relpath).stat().st_mtime for relpath in output_paths)
    return newest_input > oldest_output


def _run_with_cuda_driver(
    contract: NVGPUContract,
    kernel: NVGPUKernelContract,
    args: tuple[Any, ...],
) -> dict[str, Any]:
    cuda = _load_cuda_driver()
    context = ctypes.c_void_p()
    module = ctypes.c_void_p()
    function = ctypes.c_void_p()
    device = ctypes.c_int()
    device_allocations: list[ctypes.c_uint64] = []
    host_output_copies: list[tuple[np.ndarray, ctypes.c_uint64]] = []
    kernel_param_storage: list[Any] = []

    cubin_path = contract.package_dir / f"build/nvgpu/{Path(kernel.source).stem}.cubin"
    _check_cuda(cuda.cuInit(0), "cuInit")
    _check_cuda(cuda.cuDeviceGet(ctypes.byref(device), 0), "cuDeviceGet")
    _check_cuda(cuda.cuCtxCreate_v2(ctypes.byref(context), 0, device), "cuCtxCreate_v2")
    try:
        _check_cuda(cuda.cuModuleLoad(ctypes.byref(module), str(cubin_path).encode()), "cuModuleLoad")
        _check_cuda(
            cuda.cuModuleGetFunction(ctypes.byref(function), module, kernel.func_id.encode()),
            "cuModuleGetFunction",
        )
        arg_env = {param.name: value for param, value in zip(kernel.params, args, strict=True)}
        kernel_params = _prepare_kernel_params(
            cuda, kernel, args, device_allocations, host_output_copies, kernel_param_storage
        )
        grid = _grid_dims(kernel, arg_env)
        _check_cuda(
            cuda.cuLaunchKernel(
                function,
                grid[0],
                grid[1],
                grid[2],
                kernel.thread_block[0],
                kernel.thread_block[1],
                kernel.thread_block[2],
                0,
                ctypes.c_void_p(),
                kernel_params,
                None,
            ),
            "cuLaunchKernel",
        )
        _check_cuda(cuda.cuCtxSynchronize(), "cuCtxSynchronize")
        for host_array, device_ptr in host_output_copies:
            _check_cuda(
                cuda.cuMemcpyDtoH_v2(
                    host_array.ctypes.data_as(ctypes.c_void_p), device_ptr, host_array.nbytes
                ),
                "cuMemcpyDtoH_v2",
            )
        return {
            "adapter": "cuda_driver",
            "entry": contract.entrypoint,
            "kernel": kernel.func_id,
            "cubin": cubin_path.as_posix(),
            "thread_block": list(kernel.thread_block),
            "grid": list(grid),
            "params": [param.name for param in kernel.params],
        }
    finally:
        for _host_array, device_ptr in reversed(host_output_copies):
            _check_cuda(cuda.cuMemFree_v2(device_ptr), "cuMemFree_v2")
        remaining = [
            ptr
            for ptr in device_allocations
            if all(ptr.value != output_ptr.value for _a, output_ptr in host_output_copies)
        ]
        for device_ptr in reversed(remaining):
            _check_cuda(cuda.cuMemFree_v2(device_ptr), "cuMemFree_v2")
        if module.value:
            cuda.cuModuleUnload(module)
        if context.value:
            cuda.cuCtxDestroy_v2(context)


def _prepare_kernel_params(
    cuda: ctypes.CDLL,
    kernel: NVGPUKernelContract,
    args: tuple[Any, ...],
    device_allocations: list[ctypes.c_uint64],
    host_output_copies: list[tuple[np.ndarray, ctypes.c_uint64]],
    kernel_param_storage: list[Any],
) -> ctypes.Array[Any]:
    param_ptrs: list[ctypes.c_void_p] = []
    for param, arg in zip(kernel.params, args, strict=True):
        if param.kind == "buffer":
            host_array = _coerce_array(param, arg)
            device_ptr = ctypes.c_uint64()
            _check_cuda(cuda.cuMemAlloc_v2(ctypes.byref(device_ptr), host_array.nbytes), "cuMemAlloc_v2")
            device_allocations.append(device_ptr)
            if param.role != "output":
                _check_cuda(
                    cuda.cuMemcpyHtoD_v2(
                        device_ptr, host_array.ctypes.data_as(ctypes.c_void_p), host_array.nbytes
                    ),
                    "cuMemcpyHtoD_v2",
                )
            else:
                host_output_copies.append((host_array, device_ptr))
            kernel_param_storage.append(device_ptr)
            param_ptrs.append(ctypes.cast(ctypes.byref(device_ptr), ctypes.c_void_p))
            continue
        scalar_value = _coerce_scalar(param, arg)
        kernel_param_storage.append(scalar_value)
        param_ptrs.append(ctypes.cast(ctypes.byref(scalar_value), ctypes.c_void_p))
    return (ctypes.c_void_p * len(param_ptrs))(*param_ptrs)


def _coerce_array(param: NVGPUParamContract, arg: Any) -> np.ndarray:
    if not isinstance(arg, np.ndarray):
        raise TypeError(
            f"Expected numpy.ndarray for buffer parameter {param.name!r}, received {arg.__class__.__name__}."
        )
    if param.dtype != "f32":
        raise TypeError(f"Unsupported NV-GPU buffer dtype {param.dtype!r} for parameter {param.name!r}.")
    if arg.dtype != np.float32:
        raise TypeError(f"Expected float32 numpy array for parameter {param.name!r}, received {arg.dtype}.")
    return np.ascontiguousarray(arg)


def _coerce_scalar(param: NVGPUParamContract, arg: Any) -> Any:
    if param.dtype == "i32":
        return ctypes.c_int(int(arg))
    if param.dtype == "i64":
        return ctypes.c_longlong(int(arg))
    if param.dtype == "f32":
        return ctypes.c_float(float(arg))
    raise TypeError(f"Unsupported NV-GPU scalar dtype {param.dtype!r} for parameter {param.name!r}.")


def _grid_dims(kernel: NVGPUKernelContract, arg_env: Mapping[str, Any]) -> tuple[int, int, int]:
    if kernel.launch.kind == "grid_2d":
        rows = int(arg_env[kernel.launch.extents[0]])
        cols = int(arg_env[kernel.launch.extents[1]])
        block_x = max(1, kernel.thread_block[0])
        block_y = max(1, kernel.thread_block[1])
        grid_x = (cols + block_x - 1) // block_x
        grid_y = (rows + block_y - 1) // block_y
        return (grid_x, grid_y, 1)
    extent = int(arg_env[kernel.launch.extents[0]])
    block_x = max(1, kernel.thread_block[0])
    return ((extent + block_x - 1) // block_x, 1, 1)


def _load_cuda_driver() -> ctypes.CDLL:
    library_path = ctypes.util.find_library("cuda")
    if library_path is None:
        raise RuntimeError("CUDA driver library not found.")
    cuda = ctypes.CDLL(library_path)
    _configure_cuda_driver(cuda)
    return cuda


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
    cuda.cuModuleGetFunction.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.c_char_p]
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
    cuda.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t]
    cuda.cuMemAlloc_v2.restype = ctypes.c_int
    cuda.cuMemFree_v2.argtypes = [ctypes.c_uint64]
    cuda.cuMemFree_v2.restype = ctypes.c_int
    cuda.cuMemcpyHtoD_v2.argtypes = [ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
    cuda.cuMemcpyHtoD_v2.restype = ctypes.c_int
    cuda.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t]
    cuda.cuMemcpyDtoH_v2.restype = ctypes.c_int


def _check_cuda(code: int, operation: str) -> None:
    if code != 0:
        raise RuntimeError(f"{operation} failed with CUDA driver error code {code}.")
