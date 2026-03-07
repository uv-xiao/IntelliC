from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def eligibility_for(program: Mapping[str, Any]) -> dict[str, Any]:
    exprs = program.get("exprs")
    ok = isinstance(program.get("entry"), str) and isinstance(exprs, list)
    reasons: list[str] = []
    if not ok:
        reasons.append("program requires a string entry and a list of exprs")
    elif not all(
        isinstance(expr, Mapping)
        and expr.get("op") in {"add", "mul"}
        and isinstance(expr.get("target"), str)
        and isinstance(expr.get("lhs"), str)
        and isinstance(expr.get("rhs"), str)
        for expr in exprs
    ):
        ok = False
        reasons.append("exprs must be mappings with add/mul ops and string target/lhs/rhs")
    return {
        "schema": "htp_ext.mlir_cse.eligibility.v1",
        "ok": ok,
        "entry": program.get("entry"),
        "reasons": reasons,
    }


def export_program(program: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    exprs = program.get("exprs", [])
    lines = ["module {", f"  func.func @{program['entry']}() {{"]
    ledger_ops = []
    for index, expr in enumerate(exprs):
        op_name = "arith.addi" if expr["op"] == "add" else "arith.muli"
        result_name = f"%{index}"
        lines.append(f"    {result_name} = {op_name} %{expr['lhs']}, %{expr['rhs']}")
        ledger_ops.append(
            {
                "mlir_result": result_name,
                "target": expr["target"],
                "op": expr["op"],
                "lhs": expr["lhs"],
                "rhs": expr["rhs"],
                "entity_id": f"{program['entry']}:E{index}",
            }
        )
    lines.append("    return")
    lines.append("  }")
    lines.append("}")
    ledger = {
        "schema": "htp_ext.mlir_cse.ledger.v1",
        "entry": program["entry"],
        "ops": ledger_ops,
    }
    return "\n".join(lines) + "\n", ledger


__all__ = ["eligibility_for", "export_program"]
