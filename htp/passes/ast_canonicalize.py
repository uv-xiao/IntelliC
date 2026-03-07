from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from htp.artifacts.stages import RunnablePySpec
from htp.passes.contracts import PassContract
from htp.passes.manager import PassResult

PASS_ID = "htp::ast_canonicalize@1"

CONTRACT = PassContract(
    pass_id=PASS_ID,
    owner="htp",
    kind="transform",
    ast_effect="mutates",
    provides=("Invariant.ASTCanonical@1",),
    outputs=("ir.ast",),
)


def run(
    program: Mapping[str, Any], *, stage_before: Mapping[str, object]
) -> tuple[dict[str, Any], PassResult]:
    del stage_before

    next_program = deepcopy(dict(program))
    next_program["canonicalized"] = True
    next_program["canonical_ast"] = {
        "entry": next_program["entry"],
        "ops": [
            {
                "op_id": f"op{index}",
                "op": op_name,
            }
            for index, op_name in enumerate(next_program["ops"])
        ],
    }

    return next_program, PassResult(
        runnable_py=RunnablePySpec(status="preserves", modes=("sim",)),
        digests={"ast_hash": "demo-canonical-ast-v1"},
        time_ms=0.2,
    )


__all__ = ["CONTRACT", "PASS_ID", "run"]
