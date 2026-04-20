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
    """Base object for one structured CSP process-local step."""

    kind: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {"kind": self.kind, **dict(self.attrs)}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> CSPProcessStep:
        kind = str(payload["kind"])
        attrs = {key: value for key, value in payload.items() if key != "kind"}
        if kind == "get":
            return CSPGetStep(
                channel=str(attrs["channel"]),
                count=int(attrs.get("count", 1)),
                attrs={key: value for key, value in attrs.items() if key not in {"channel", "count"}},
            )
        if kind == "put":
            return CSPPutStep(
                channel=str(attrs["channel"]),
                count=int(attrs.get("count", 1)),
                value=attrs.get("value"),
                attrs={
                    key: value for key, value in attrs.items() if key not in {"channel", "count", "value"}
                },
            )
        if kind == "compute":
            op = attrs.get("op", attrs.get("name"))
            return CSPComputeStep(
                op=str(op),
                result=attrs.get("result"),
                attrs={key: value for key, value in attrs.items() if key not in {"op", "name", "result"}},
            )
        return cls(
            kind=kind,
            attrs=attrs,
        )


@dataclass(frozen=True, init=False)
class CSPGetStep(CSPProcessStep):
    """Typed receive step from a named CSP channel."""

    channel: str
    count: int

    def __init__(self, *, channel: str, count: int = 1, attrs: Mapping[str, Any] | None = None) -> None:
        payload = {"channel": channel, "count": int(count), **dict(attrs or {})}
        object.__setattr__(self, "kind", "get")
        object.__setattr__(self, "attrs", payload)
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "count", int(count))


@dataclass(frozen=True, init=False)
class CSPPutStep(CSPProcessStep):
    """Typed send step to a named CSP channel."""

    channel: str
    count: int
    value: Any | None

    def __init__(
        self,
        *,
        channel: str,
        count: int = 1,
        value: Any | None = None,
        attrs: Mapping[str, Any] | None = None,
    ) -> None:
        payload = {"channel": channel, "count": int(count), **dict(attrs or {})}
        if value is not None:
            payload["value"] = value
        object.__setattr__(self, "kind", "put")
        object.__setattr__(self, "attrs", payload)
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "count", int(count))
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, init=False)
class CSPComputeStep(CSPProcessStep):
    """Typed process-local compute operation."""

    op: str
    result: Any | None

    def __init__(
        self,
        *,
        op: str,
        result: Any | None = None,
        attrs: Mapping[str, Any] | None = None,
    ) -> None:
        payload = {"op": op, **dict(attrs or {})}
        if result is not None:
            payload["result"] = result
        object.__setattr__(self, "kind", "compute")
        object.__setattr__(self, "attrs", payload)
        object.__setattr__(self, "op", op)
        object.__setattr__(self, "result", result)


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


__all__ = [
    "CSPComputeStep",
    "CSPGetStep",
    "CSPProcessStep",
    "CSPPutStep",
    "steps_from_payload",
    "steps_to_payload",
]
