from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .pipeline import PipelineRun


@dataclass(frozen=True)
class CompilerAction:
    name: str
    apply: Callable[[PipelineRun], None]

    def run(self, run: PipelineRun) -> None:
        run.db.put("ActionRun", self.name, {"name": self.name})
        self.apply(run)
