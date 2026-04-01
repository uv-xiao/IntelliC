"""Typed nested CSP process-step structures.

These objects replace nested dict ownership for process-local CSP steps while
preserving the existing payload contract at serialization boundaries.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CSPProcessStep:
    """One structured CSP process-local step."""

    kind: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"kind": self.kind, **dict(self.attrs)}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> CSPProcessStep:
        return cls(
            kind=str(payload["kind"]),
            attrs={key: value for key, value in payload.items() if key != "kind"},
        )


def steps_from_payload(payload: Sequence[Any]) -> list[CSPProcessStep]:
    steps: list[CSPProcessStep] = []
    for item in payload:
        if isinstance(item, CSPProcessStep):
            steps.append(item)
        elif isinstance(item, Mapping):
            steps.append(CSPProcessStep.from_payload(item))
    return steps


def steps_to_payload(steps: Sequence[CSPProcessStep]) -> list[dict[str, Any]]:
    return [step.to_payload() for step in steps]


__all__ = ["CSPProcessStep", "steps_from_payload", "steps_to_payload"]
