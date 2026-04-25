from __future__ import annotations

from dataclasses import dataclass

from intellic.ir.syntax import Operation, Value


@dataclass(frozen=True)
class MutationIntent:
    kind: str
    subject: Operation
    replacement: Value | None = None
    reason: str = ""


@dataclass(frozen=True)
class MutationApplied:
    intent: MutationIntent


@dataclass(frozen=True)
class MutationRejected:
    intent: MutationIntent
    reason: str
