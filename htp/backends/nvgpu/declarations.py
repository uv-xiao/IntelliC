from __future__ import annotations

from pathlib import PurePosixPath

from htp.backends.declarations import ArtifactContract, BackendSolverDeclaration

from .arch import arch_for, normalize_profile

NVGPU_PROJECT_DIR = PurePosixPath("codegen/nvgpu")
NVGPU_TOOLCHAIN_PATH = PurePosixPath("build/toolchain.json")


def declaration_for(profile: str | None = None) -> BackendSolverDeclaration:
    arch = arch_for(normalize_profile(profile))
    codegen_index = (NVGPU_PROJECT_DIR / "nvgpu_codegen.json").as_posix()
    target_capabilities = tuple(f"Target.{arch.backend}.{capability}@1" for capability in arch.capabilities)
    supported_ops = [
        "elementwise_binary",
        "elementwise_unary",
        "matmul",
        "async_copy",
        "barrier",
        "broadcast",
        "channel_recv",
        "channel_send",
        "commit",
        "mma",
        "reduction_sum",
    ]
    if arch.profile == "ampere":
        supported_ops.extend(["cp_async", "ldmatrix", "mma_sync"])
    else:
        supported_ops.extend(["tma_load", "wgmma", "tma_store"])
    return BackendSolverDeclaration(
        backend=arch.backend,
        variant=arch.variant,
        hardware_profile=arch.hardware_profile,
        target_capabilities=target_capabilities,
        supported_ops=tuple(supported_ops),
        selection_cost=40 if arch.hardware_profile.startswith("nvidia-blackwell") else 30,
        artifact_contract=ArtifactContract(
            outputs=(
                ("nvgpu_codegen_index", codegen_index),
                ("toolchain_manifest", NVGPU_TOOLCHAIN_PATH.as_posix()),
            )
        ),
    )


__all__ = ["declaration_for"]
