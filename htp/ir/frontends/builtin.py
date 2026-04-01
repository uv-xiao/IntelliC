"""Builtin frontend registrations and workload adapter helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.semantics import WorkloadChannel, WorkloadDependency, WorkloadTask
from ..dialects.csp import csp_frontend_workload
from ..dialects.wsp import wsp_frontend_workload
from .registry import FrontendSpec, frontend_registry_snapshot, register_frontend
from .rules import FrontendRule, FrontendRuleResult, ProgramSurfaceRule
from .shared import FrontendWorkload


@dataclass(frozen=True)
class BuiltinFrontendRegistration:
    """Built-in frontend registration description with separated workload glue."""

    frontend_id: str
    dialect_id: str
    surface_type: type[Any]
    rule: FrontendRule

    def to_spec(self) -> FrontendSpec:
        return FrontendSpec(
            frontend_id=self.frontend_id,
            dialect_id=self.dialect_id,
            surface_type=self.surface_type,
            rule=self.rule,
        )


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
        channels=tuple(
            WorkloadChannel(
                name=channel.name,
                dtype=channel.dtype,
                capacity=channel.capacity,
                protocol=channel.protocol,
            )
            for channel in surface.channels
        ),
        dependencies=tuple(
            WorkloadDependency(src=dependency.src, dst=dependency.dst)
            for dependency in surface.dependencies
        ),
        routine={
            "kind": "routine",
            "entry": surface.entry,
            "target": dict(surface.target or {}),
        },
    )


def _builtin_registrations() -> tuple[BuiltinFrontendRegistration, ...]:
    from htp.csp import CSPProgramSpec
    from htp.kernel import KernelSpec, build_kernel_program_module
    from htp.routine import ProgramSpec
    from htp.wsp import WSPProgramSpec

    return (
        BuiltinFrontendRegistration(
            frontend_id="htp.kernel.KernelSpec",
            dialect_id="htp.kernel",
            surface_type=KernelSpec,
            rule=FrontendRule(
                name="kernel_spec_to_program_module",
                build=lambda context: FrontendRuleResult(module=build_kernel_program_module(context.surface)),
            ),
        ),
        BuiltinFrontendRegistration(
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
        BuiltinFrontendRegistration(
            frontend_id="htp.wsp.WSPProgramSpec",
            dialect_id="htp.wsp",
            surface_type=WSPProgramSpec,
            rule=ProgramSurfaceRule(
                name="wsp_spec_to_program_module",
                source_surface="htp.wsp.WSPProgramSpec",
                active_dialects=("htp.core", "htp.kernel", "htp.wsp"),
                kernel_spec=lambda surface: surface.kernel_spec(),
                authored_program=lambda surface: surface.to_program(),
                workload=wsp_frontend_workload,
            ),
        ),
        BuiltinFrontendRegistration(
            frontend_id="htp.csp.CSPProgramSpec",
            dialect_id="htp.csp",
            surface_type=CSPProgramSpec,
            rule=ProgramSurfaceRule(
                name="csp_spec_to_program_module",
                source_surface="htp.csp.CSPProgramSpec",
                active_dialects=("htp.core", "htp.kernel", "htp.csp"),
                kernel_spec=lambda surface: surface.kernel_spec(),
                authored_program=lambda surface: surface.to_program(),
                workload=csp_frontend_workload,
            ),
        ),
    )


def ensure_builtin_frontends() -> tuple[FrontendSpec, ...]:
    registrations = _builtin_registrations()
    snapshot = frontend_registry_snapshot()
    for registration in registrations:
        if registration.frontend_id not in snapshot:
            register_frontend(registration.to_spec())
    updated = frontend_registry_snapshot()
    return tuple(updated[registration.frontend_id] for registration in registrations)


__all__ = ["BuiltinFrontendRegistration", "ensure_builtin_frontends"]
