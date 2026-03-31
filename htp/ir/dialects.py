from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DialectExports:
    nodes: tuple[str, ...] = ()
    aspects: tuple[str, ...] = ()
    analyses: tuple[str, ...] = ()
    intrinsics: tuple[str, ...] = ()
    frontends: tuple[str, ...] = ()
    interpreters: tuple[str, ...] = ()
    passes: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, list[str]]:
        return {
            "nodes": list(self.nodes),
            "aspects": list(self.aspects),
            "analyses": list(self.analyses),
            "intrinsics": list(self.intrinsics),
            "frontends": list(self.frontends),
            "interpreters": list(self.interpreters),
            "passes": list(self.passes),
        }


@dataclass(frozen=True)
class DialectSpec:
    dialect_id: str
    version: str
    kind: str
    dependencies: tuple[str, ...] = ()
    owner: str = "builtin"
    exports: DialectExports = field(default_factory=DialectExports)

    def to_payload(self) -> dict[str, Any]:
        return {
            "dialect_id": self.dialect_id,
            "version": self.version,
            "kind": self.kind,
            "dependencies": list(self.dependencies),
            "owner": self.owner,
            "exports": self.exports.to_payload(),
        }


@dataclass(frozen=True)
class DialectActivation:
    requested: tuple[str, ...]
    resolved: tuple[DialectSpec, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "requested": list(self.requested),
            "resolved": [spec.to_payload() for spec in self.resolved],
        }

    def dialect_ids(self) -> tuple[str, ...]:
        return tuple(spec.dialect_id for spec in self.resolved)


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
    ensure_builtin_dialects()
    requested = _dedupe_dialect_ids(active)
    resolved: list[DialectSpec] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(dialect_id: str) -> None:
        if dialect_id in visited:
            return
        if dialect_id in visiting:
            raise ValueError(f"Cyclic dialect dependency detected at {dialect_id!r}")
        visiting.add(dialect_id)
        spec = get_dialect(dialect_id)
        for dependency in spec.dependencies:
            visit(dependency)
        visiting.remove(dialect_id)
        visited.add(dialect_id)
        resolved.append(spec)

    for dialect_id in requested:
        visit(dialect_id)
    return tuple(resolved)


def activate_dialects(*dialect_ids: str) -> DialectActivation:
    requested = _dedupe_dialect_ids(dialect_ids)
    resolved = resolve_dialects(requested)
    return DialectActivation(requested=requested, resolved=resolved)


def dialect_activation_payload(*dialect_ids: str) -> dict[str, Any]:
    activation = activate_dialects(*dialect_ids)
    return {
        "active_dialects": list(activation.dialect_ids()),
        "dialect_activation": activation.to_payload(),
    }


def ensure_builtin_dialects() -> tuple[DialectSpec, ...]:
    builtin = (
        DialectSpec(
            dialect_id="htp.core",
            version="v1",
            kind="core",
            exports=DialectExports(
                nodes=("ProgramModule", "ProgramItems", "ProgramAspects", "ProgramIdentity"),
                aspects=("TypesAspect", "LayoutAspect", "EffectsAspect", "ScheduleAspect"),
                analyses=("AnalysisRecord",),
                interpreters=("snapshot",),
            ),
        ),
        DialectSpec(
            dialect_id="htp.kernel",
            version="v1",
            kind="frontend",
            dependencies=("htp.core",),
            exports=DialectExports(
                nodes=("KernelSpec", "KernelArgSpec", "KernelValue"),
                frontends=("kernel",),
            ),
        ),
        DialectSpec(
            dialect_id="htp.routine",
            version="v1",
            kind="frontend",
            dependencies=("htp.core", "htp.kernel"),
            exports=DialectExports(
                nodes=("ProgramSpec", "KernelCallSpec", "ChannelSpec"),
                frontends=("program",),
            ),
        ),
        DialectSpec(
            dialect_id="htp.wsp",
            version="v1",
            kind="frontend",
            dependencies=("htp.core", "htp.kernel"),
            exports=DialectExports(
                nodes=("WSPProgramSpec", "WSPBuilder", "WSPTaskBuilder"),
                frontends=("wsp.program",),
            ),
        ),
        DialectSpec(
            dialect_id="htp.csp",
            version="v1",
            kind="frontend",
            dependencies=("htp.core", "htp.kernel"),
            exports=DialectExports(
                nodes=("CSPProgramSpec", "CSPBuilder", "CSPProcessBuilder"),
                frontends=("csp.program",),
            ),
        ),
    )
    for spec in builtin:
        if spec.dialect_id not in _DIALECT_REGISTRY:
            register_dialect(spec)
    return tuple(_DIALECT_REGISTRY[spec.dialect_id] for spec in builtin)


def normalize_active_dialects(*dialect_ids: str) -> tuple[str, ...]:
    return activate_dialects(*dialect_ids).dialect_ids()


def _dedupe_dialect_ids(dialect_ids: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for dialect_id in dialect_ids:
        normalized = str(dialect_id)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


__all__ = [
    "DialectActivation",
    "DialectExports",
    "DialectSpec",
    "activate_dialects",
    "dialect_activation_payload",
    "dialect_registry_snapshot",
    "ensure_builtin_dialects",
    "get_dialect",
    "normalize_active_dialects",
    "register_dialect",
    "resolve_dialects",
]
