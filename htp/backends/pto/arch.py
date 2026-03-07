from __future__ import annotations

from dataclasses import dataclass

BACKEND = "pto"
DEFAULT_VARIANT = "a2a3sim"
SUPPORTED_VARIANTS = ("a2a3sim", "a2a3")


@dataclass(frozen=True)
class PTOArch:
    backend: str
    variant: str
    hardware_profile: str
    core_type: str = "aiv"
    memory_spaces: tuple[str, ...] = ("gm", "ub")


def normalize_variant(variant: str | None) -> str:
    resolved = DEFAULT_VARIANT if variant is None else variant
    if resolved not in SUPPORTED_VARIANTS:
        supported = ", ".join(SUPPORTED_VARIANTS)
        raise ValueError(f"Unsupported PTO variant {resolved!r}; expected one of: {supported}")
    return resolved


def arch_for(variant: str | None = None) -> PTOArch:
    resolved = normalize_variant(variant)
    return PTOArch(
        backend=BACKEND,
        variant=resolved,
        hardware_profile=f"ascend:{resolved}",
    )


__all__ = [
    "BACKEND",
    "DEFAULT_VARIANT",
    "PTOArch",
    "SUPPORTED_VARIANTS",
    "arch_for",
    "normalize_variant",
]
