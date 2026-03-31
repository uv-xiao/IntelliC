from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .frontend import FrontendWorkload
from .frontend_rules import FrontendBuildContext, FrontendRule, FrontendRuleResult, ProgramSurfaceRule
from .module import ProgramModule
from .semantics import WorkloadTask


@dataclass(frozen=True)
class FrontendSpec:
    frontend_id: str
    dialect_id: str
    surface_type: type[Any]
    build_program_module: Callable[[Any], ProgramModule] | None = None
    rule: FrontendRule | None = None

    def build(self, surface: Any) -> ProgramModule:
        if self.rule is not None:
            result = self.rule.apply(
                FrontendBuildContext(
                    frontend_id=self.frontend_id,
                    dialect_id=self.dialect_id,
                    surface=surface,
                )
            )
            if not isinstance(result.module, ProgramModule):
                raise TypeError(f"{self.frontend_id} rule must return a ProgramModule")
            return result.module
        if self.build_program_module is None:
            raise TypeError(f"{self.frontend_id} has no builder or rule")
        module = self.build_program_module(surface)
        if not isinstance(module, ProgramModule):
            raise TypeError(f"{self.frontend_id} must build a ProgramModule")
        return module


_FRONTEND_REGISTRY: dict[str, FrontendSpec] = {}


def _routine_frontend_workload(surface: Any) -> FrontendWorkload:
    return FrontendWorkload(
        entry=surface.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=task.task_id,
                kind=task.kind,
                kernel=task.kernel,
                args=task.args,
                entity_id=f"{surface.entry}:{task.task_id}",
                attrs={} if task.attrs is None else dict(task.attrs),
            )
            for task in surface.tasks
        ),
        channels=tuple(channel.to_payload() for channel in surface.channels),
        dependencies=tuple(dependency.to_payload() for dependency in surface.dependencies),
        routine={
            "kind": "routine",
            "entry": surface.entry,
            "target": dict(surface.target or {}),
        },
    )


def _wsp_frontend_workload(surface: Any) -> FrontendWorkload:
    return FrontendWorkload(
        entry=surface.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=str(task["task_id"]),
                kind=str(task["kind"]),
                kernel=str(task["kernel"]),
                args=tuple(str(arg) for arg in task.get("args", ())),
                entity_id=f"{surface.entry}:{task['task_id']}",
                attrs=dict(task.get("attrs", {})),
            )
            for task in surface.workload.get("tasks", ())
        ),
        channels=tuple(dict(item) for item in surface.workload.get("channels", ())),
        dependencies=tuple(dict(item) for item in surface.workload.get("dependencies", ())),
        routine={
            "kind": "wsp",
            "entry": surface.entry,
            "schedule": {key: dict(value) for key, value in surface.schedule.items()},
            "target": dict(surface.target),
        },
    )


def _csp_frontend_workload(surface: Any) -> FrontendWorkload:
    return FrontendWorkload(
        entry=surface.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=str(process["task_id"]),
                kind="process",
                kernel=str(process["kernel"]),
                args=tuple(str(arg) for arg in process.get("args", ())),
                entity_id=f"{surface.entry}:{process['task_id']}",
                attrs={
                    "name": str(process["name"]),
                    **({"role": str(process["role"])} if process.get("role") is not None else {}),
                },
            )
            for process in surface.processes
        ),
        channels=tuple(dict(item) for item in surface.channels),
        dependencies=(),
        processes=tuple(dict(item) for item in surface.processes),
        routine={
            "kind": "csp",
            "entry": surface.entry,
            "target": dict(surface.target),
        },
    )


def register_frontend(spec: FrontendSpec, *, replace: bool = False) -> None:
    existing = _FRONTEND_REGISTRY.get(spec.frontend_id)
    if existing is not None and not replace:
        raise ValueError(f"Frontend {spec.frontend_id!r} is already registered")
    _FRONTEND_REGISTRY[spec.frontend_id] = spec


def frontend_registry_snapshot() -> dict[str, FrontendSpec]:
    return dict(_FRONTEND_REGISTRY)


def ensure_builtin_frontends() -> tuple[FrontendSpec, ...]:
    from htp.csp import CSPProgramSpec
    from htp.kernel import KernelSpec, build_kernel_program_module
    from htp.routine import ProgramSpec
    from htp.wsp import WSPProgramSpec

    builtin = (
        FrontendSpec(
            frontend_id="htp.kernel.KernelSpec",
            dialect_id="htp.kernel",
            surface_type=KernelSpec,
            rule=FrontendRule(
                name="kernel_spec_to_program_module",
                build=lambda context: FrontendRuleResult(module=build_kernel_program_module(context.surface)),
            ),
        ),
        FrontendSpec(
            frontend_id="htp.routine.ProgramSpec",
            dialect_id="htp.routine",
            surface_type=ProgramSpec,
            rule=ProgramSurfaceRule(
                name="routine_spec_to_program_module",
                source_surface="htp.routine.ProgramSpec",
                active_dialects=("htp.core", "htp.kernel", "htp.routine"),
                kernel_spec=lambda surface: surface.kernel,
                authored_program=lambda surface: surface.to_program(),
                workload=_routine_frontend_workload,
            ),
        ),
        FrontendSpec(
            frontend_id="htp.wsp.WSPProgramSpec",
            dialect_id="htp.wsp",
            surface_type=WSPProgramSpec,
            rule=ProgramSurfaceRule(
                name="wsp_spec_to_program_module",
                source_surface="htp.wsp.WSPProgramSpec",
                active_dialects=("htp.core", "htp.kernel", "htp.wsp"),
                kernel_spec=lambda surface: surface.kernel_spec(),
                authored_program=lambda surface: surface.to_program(),
                workload=_wsp_frontend_workload,
            ),
        ),
        FrontendSpec(
            frontend_id="htp.csp.CSPProgramSpec",
            dialect_id="htp.csp",
            surface_type=CSPProgramSpec,
            rule=ProgramSurfaceRule(
                name="csp_spec_to_program_module",
                source_surface="htp.csp.CSPProgramSpec",
                active_dialects=("htp.core", "htp.kernel", "htp.csp"),
                kernel_spec=lambda surface: surface.kernel_spec(),
                authored_program=lambda surface: surface.to_program(),
                workload=_csp_frontend_workload,
            ),
        ),
    )
    for spec in builtin:
        if spec.frontend_id not in _FRONTEND_REGISTRY:
            register_frontend(spec)
    return tuple(_FRONTEND_REGISTRY[spec.frontend_id] for spec in builtin)


def resolve_frontend(surface: Any) -> FrontendSpec | None:
    ensure_builtin_frontends()
    for spec in _FRONTEND_REGISTRY.values():
        if isinstance(surface, spec.surface_type):
            return spec
    return None


__all__ = [
    "FrontendSpec",
    "ensure_builtin_frontends",
    "frontend_registry_snapshot",
    "register_frontend",
    "resolve_frontend",
]
