"""WSP-specific frontend lowering helpers."""

from __future__ import annotations

from htp.ir.core.semantics import WorkloadTask
from htp.ir.frontends.shared import FrontendWorkload


def wsp_frontend_workload(surface: object) -> FrontendWorkload:
    return FrontendWorkload(
        entry=surface.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=task.task_id,
                kind=task.kind,
                kernel=task.kernel,
                args=task.args,
                entity_id=f"{surface.entry}:{task.task_id}",
                attrs=dict(task.attrs),
            )
            for task in surface.tasks
        ),
        channels=tuple(dict(item) for item in surface.channels),
        dependencies=tuple(dependency.to_payload() for dependency in surface.dependencies),
        routine={
            "kind": "wsp",
            "entry": surface.entry,
            "schedule": surface.schedule.to_payload(),
            "target": dict(surface.target),
        },
    )


__all__ = ["wsp_frontend_workload"]
