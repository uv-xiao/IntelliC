"""CSP-specific frontend lowering helpers."""

from __future__ import annotations

from htp.ir.core.semantics import WorkloadTask
from htp.ir.frontends.shared import FrontendWorkload


def csp_frontend_workload(surface: object) -> FrontendWorkload:
    return FrontendWorkload(
        entry=surface.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=process.task_id,
                kind="process",
                kernel=process.kernel,
                args=process.args,
                entity_id=f"{surface.entry}:{process.task_id}",
                attrs={"name": process.name, **({"role": process.role} if process.role is not None else {})},
            )
            for process in surface.processes
        ),
        channels=tuple(channel.to_payload() for channel in surface.channels),
        dependencies=(),
        processes=tuple(process.to_payload() for process in surface.processes),
        routine={"kind": "csp", "entry": surface.entry, "target": dict(surface.target)},
    )


__all__ = ["csp_frontend_workload"]
