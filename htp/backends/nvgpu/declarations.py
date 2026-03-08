from __future__ import annotations

from htp.backends.declarations import BackendSolverDeclaration

from .arch import arch_for, normalize_profile
from .emit import NVGPU_PROJECT_DIR, NVGPU_TOOLCHAIN_PATH


def declaration_for(profile: str | None = None) -> BackendSolverDeclaration:
    arch = arch_for(normalize_profile(profile))
    codegen_index = (NVGPU_PROJECT_DIR / "nvgpu_codegen.json").as_posix()
    target_capabilities = tuple(f"Target.{arch.backend}.{capability}@1" for capability in arch.capabilities)
    return BackendSolverDeclaration(
        backend=arch.backend,
        variant=arch.variant,
        hardware_profile=arch.hardware_profile,
        target_capabilities=target_capabilities,
        supported_ops=("elementwise_binary", "matmul"),
        required_outputs=(codegen_index, NVGPU_TOOLCHAIN_PATH.as_posix()),
    )


__all__ = ["declaration_for"]
