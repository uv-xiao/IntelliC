from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DialectSpec:
    dialect_id: str
    version: str
    kind: str
    exports: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    owner: str = "builtin"


_DIALECT_REGISTRY: dict[str, DialectSpec] = {}


def register_dialect(spec: DialectSpec, *, replace: bool = False) -> None:
    existing = _DIALECT_REGISTRY.get(spec.dialect_id)
    if existing is not None and not replace:
        raise ValueError(f"Dialect {spec.dialect_id!r} is already registered")
    _DIALECT_REGISTRY[spec.dialect_id] = spec


def get_dialect(dialect_id: str) -> DialectSpec:
    try:
        return _DIALECT_REGISTRY[dialect_id]
    except KeyError as exc:
        raise KeyError(f"Unknown dialect {dialect_id!r}") from exc


def dialect_registry_snapshot() -> dict[str, DialectSpec]:
    return dict(_DIALECT_REGISTRY)


def resolve_dialects(active: Sequence[str]) -> tuple[DialectSpec, ...]:
    return tuple(get_dialect(dialect_id) for dialect_id in active)


def ensure_builtin_dialects() -> tuple[DialectSpec, ...]:
    builtin = (
        DialectSpec(
            dialect_id="htp.core",
            version="v1",
            kind="core",
            exports=("ProgramModule", "ProgramItems", "ProgramAspects", "ProgramIdentity"),
        ),
        DialectSpec(
            dialect_id="htp.kernel",
            version="v1",
            kind="frontend",
            exports=("KernelSpec", "KernelArgSpec", "KernelValue"),
            dependencies=("htp.core",),
        ),
        DialectSpec(
            dialect_id="htp.routine",
            version="v1",
            kind="frontend",
            exports=("ProgramSpec", "KernelCallSpec", "ChannelSpec"),
            dependencies=("htp.core", "htp.kernel"),
        ),
        DialectSpec(
            dialect_id="htp.wsp",
            version="v1",
            kind="frontend",
            exports=("WSPProgramSpec", "WSPBuilder", "WSPTaskBuilder"),
            dependencies=("htp.core", "htp.kernel"),
        ),
        DialectSpec(
            dialect_id="htp.csp",
            version="v1",
            kind="frontend",
            exports=("CSPProgramSpec", "CSPBuilder", "CSPProcessBuilder"),
            dependencies=("htp.core", "htp.kernel"),
        ),
    )
    for spec in builtin:
        if spec.dialect_id not in _DIALECT_REGISTRY:
            register_dialect(spec)
    return tuple(_DIALECT_REGISTRY[spec.dialect_id] for spec in builtin)


def normalize_active_dialects(*dialect_ids: str) -> tuple[str, ...]:
    ensure_builtin_dialects()
    resolved = resolve_dialects(dialect_ids)
    return tuple(spec.dialect_id for spec in resolved)


__all__ = [
    "DialectSpec",
    "dialect_registry_snapshot",
    "ensure_builtin_dialects",
    "get_dialect",
    "normalize_active_dialects",
    "register_dialect",
    "resolve_dialects",
]
