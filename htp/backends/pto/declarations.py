from __future__ import annotations

from htp.backends.declarations import BackendSolverDeclaration

from .arch import arch_for, normalize_variant
from .emit import PTO_PROJECT_DIR, PTO_TOOLCHAIN_PATH


def declaration_for(variant: str | None = None) -> BackendSolverDeclaration:
    arch = arch_for(normalize_variant(variant))
    target_capabilities = (
        f"Target.{arch.backend}.CoreType.{arch.core_type}@1",
        *(f"Target.{arch.backend}.MemorySpace.{space}@1" for space in arch.memory_spaces),
    )
    return BackendSolverDeclaration(
        backend=arch.backend,
        variant=arch.variant,
        hardware_profile=arch.hardware_profile,
        target_capabilities=target_capabilities,
        supported_ops=("elementwise_binary",),
        required_outputs=(
            (PTO_PROJECT_DIR / "kernel_config.py").as_posix(),
            (PTO_PROJECT_DIR / "pto_codegen.json").as_posix(),
            PTO_TOOLCHAIN_PATH.as_posix(),
        ),
    )


__all__ = ["declaration_for"]
