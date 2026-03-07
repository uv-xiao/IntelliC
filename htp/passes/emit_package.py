from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult

PASS_ID = "htp::emit_package@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="mixed",
    ast_effect="preserves",
    requires=("Schedule.Applied@1",),
    provides=("Package.Emitted@1",),
    outputs=("manifest", "package"),
)


def run(program: Mapping[str, Any], *, stage_before: Mapping[str, object]) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    next_program["package"] = {
        "emitted": True,
        "entry": next_program["entry"],
    }

    return next_program, PassResult(
        runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        time_ms=0.1,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
