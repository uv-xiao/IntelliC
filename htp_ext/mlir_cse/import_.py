from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def import_program(program: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    exprs = program["exprs"]
    seen: dict[tuple[str, str, str], str] = {}
    imported_exprs: list[dict[str, Any]] = []
    rewrites: list[dict[str, str]] = []
    aliases: dict[str, str] = {}

    for expr in exprs:
        lhs = aliases.get(expr["lhs"], expr["lhs"])
        rhs = aliases.get(expr["rhs"], expr["rhs"])
        signature = (expr["op"], lhs, rhs)
        existing = seen.get(signature)
        if existing is not None:
            aliases[expr["target"]] = existing
            rewrites.append(
                {
                    "eliminated_target": expr["target"],
                    "reused_target": existing,
                    "signature": f"{expr['op']}({lhs}, {rhs})",
                }
            )
            continue
        imported_expr = {
            "target": expr["target"],
            "op": expr["op"],
            "lhs": lhs,
            "rhs": rhs,
        }
        imported_exprs.append(imported_expr)
        seen[signature] = expr["target"]

    imported_program = {
        "entry": program["entry"],
        "exprs": imported_exprs,
        "inputs": tuple(
            dict.fromkeys(
                operand
                for expr in imported_exprs
                for operand in (expr["lhs"], expr["rhs"])
                if operand not in {item["target"] for item in imported_exprs}
            )
        ),
        "result": aliases.get(program["result"], program["result"]),
    }
    summary = {
        "schema": "htp_ext.mlir_cse.import_summary.v1",
        "entry": program["entry"],
        "rewrites": rewrites,
        "result": imported_program["result"],
    }
    return imported_program, summary


__all__ = ["import_program"]
