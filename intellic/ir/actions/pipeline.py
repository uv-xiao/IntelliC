from __future__ import annotations

from dataclasses import dataclass, field

from intellic.ir.semantics import TraceDB
from intellic.ir.syntax import Operation


@dataclass
class PipelineRun:
    module: Operation
    db: TraceDB = field(default_factory=TraceDB)
