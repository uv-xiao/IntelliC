from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    """Source or generated location attached to syntax objects."""

    kind: str = "generated"
    file: str | None = None
    line: int | None = None
    column: int | None = None
    evidence: str | None = None


GENERATED = SourceLocation()
