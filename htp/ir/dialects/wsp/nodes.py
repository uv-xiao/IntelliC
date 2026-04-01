"""Typed nested WSP stage structures.

These objects replace nested dict ownership for stage plans inside WSP task
attributes while preserving the existing payload contract at serialization
boundaries.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WSPStageStep:
    """One structured WSP stage step."""

    op: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"kind": "step", "op": self.op, **dict(self.attrs)}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> WSPStageStep:
        return cls(
            op=str(payload["op"]),
            attrs={key: value for key, value in payload.items() if key not in {"kind", "op"}},
        )


@dataclass
class WSPStageSpec:
    """Typed WSP stage plan attached to a task."""

    name: str
    steps: list[str | WSPStageStep] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "steps": [step if isinstance(step, str) else step.to_payload() for step in self.steps],
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> WSPStageSpec:
        steps: list[str | WSPStageStep] = []
        for step in payload.get("steps", ()):
            if isinstance(step, str):
                steps.append(step)
            elif isinstance(step, Mapping):
                steps.append(WSPStageStep.from_payload(step))
        return cls(name=str(payload["name"]), steps=steps)



def stages_from_payload(payload: Any) -> list[WSPStageSpec]:
    if not isinstance(payload, list):
        return []
    stages: list[WSPStageSpec] = []
    for item in payload:
        if isinstance(item, WSPStageSpec):
            stages.append(item)
        elif isinstance(item, Mapping):
            stages.append(WSPStageSpec.from_payload(item))
    return stages


def stages_to_payload(stages: list[WSPStageSpec] | tuple[WSPStageSpec, ...]) -> list[dict[str, Any]]:
    return [stage.to_payload() for stage in stages]


__all__ = ["WSPStageSpec", "WSPStageStep", "stages_from_payload", "stages_to_payload"]
