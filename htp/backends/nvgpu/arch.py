from __future__ import annotations

from dataclasses import dataclass

BACKEND = "nvgpu"
DEFAULT_PROFILE = "ampere"
SUPPORTED_PROFILES = ("ampere", "blackwell")
DEFAULT_VARIANT = "cuda"


@dataclass(frozen=True)
class NVGPUArch:
    backend: str
    variant: str
    profile: str
    hardware_profile: str
    memory_spaces: tuple[str, ...] = ("global", "shared", "register")
    cuda_arches: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()


def normalize_profile(profile: str | None) -> str:
    resolved = DEFAULT_PROFILE if profile is None else profile
    if resolved not in SUPPORTED_PROFILES:
        supported = ", ".join(SUPPORTED_PROFILES)
        raise ValueError(f"Unsupported NV-GPU profile {resolved!r}; expected one of: {supported}")
    return resolved


def arch_for(profile: str | None = None) -> NVGPUArch:
    resolved = normalize_profile(profile)
    if resolved == "ampere":
        return NVGPUArch(
            backend=BACKEND,
            variant=DEFAULT_VARIANT,
            profile=resolved,
            hardware_profile="nvidia:ampere:sm80",
            cuda_arches=("sm80",),
            capabilities=("cp.async", "mma.sync"),
        )
    return NVGPUArch(
        backend=BACKEND,
        variant=DEFAULT_VARIANT,
        profile=resolved,
        hardware_profile="nvidia:blackwell:sm100",
        cuda_arches=("sm100",),
        capabilities=("cp.async.bulk", "tma", "wgmma"),
    )


__all__ = [
    "BACKEND",
    "DEFAULT_PROFILE",
    "DEFAULT_VARIANT",
    "NVGPUArch",
    "SUPPORTED_PROFILES",
    "arch_for",
    "normalize_profile",
]
