from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def eligibility_for(program: Mapping[str, Any]) -> dict[str, Any]:
    exprs = program.get("exprs")
    reasons: list[str] = []
    ok = isinstance(program.get("entry"), str) and isinstance(exprs, list)
    result = program.get("result")
    if not ok:
        reasons.append("program requires a string entry and a list of exprs")
    else:
        if not isinstance(result, str) or not result:
            ok = False
            reasons.append("program requires a non-empty string result symbol")
        if not all(
            isinstance(expr, Mapping)
            and expr.get("op") in {"add", "mul"}
            and isinstance(expr.get("target"), str)
            and isinstance(expr.get("lhs"), str)
            and isinstance(expr.get("rhs"), str)
            for expr in exprs
        ):
            ok = False
            reasons.append("exprs must be mappings with add/mul ops and string target/lhs/rhs")
        if ok:
            analysis = analyze_program(program)
            if result not in analysis["available_symbols"]:
                ok = False
                reasons.append("program result must reference an available symbol")
    return {
        "schema": "htp_ext.mlir_cse.eligibility.v1",
        "ok": ok,
        "entry": program.get("entry"),
        "result": result,
        "reasons": reasons,
    }


def export_program(program: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    analysis = analyze_program(program)
    exprs = program.get("exprs", [])
    arguments = ", ".join(f"%{name}: i32" for name in analysis["inputs"])
    lines = [
        "module {",
        f"  func.func @{program['entry']}({arguments}) -> i32 {{",
    ]
    value_names = {name: f"%{name}" for name in analysis["inputs"]}
    ledger_ops = []
    for index, expr in enumerate(exprs):
        op_name = "arith.addi" if expr["op"] == "add" else "arith.muli"
        result_name = f"%v{index}"
        lhs = value_names[expr["lhs"]]
        rhs = value_names[expr["rhs"]]
        lines.append(f"    {result_name} = {op_name} {lhs}, {rhs} : i32")
        value_names[expr["target"]] = result_name
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
    lines.append(f"    return {value_names[program['result']]} : i32")
    lines.append("  }")
    lines.append("}")
    ledger = {
        "schema": "htp_ext.mlir_cse.ledger.v1",
        "entry": program["entry"],
        "inputs": analysis["inputs"],
        "result": program["result"],
        "ops": ledger_ops,
    }
    return "\n".join(lines) + "\n", ledger


def analyze_program(program: Mapping[str, Any]) -> dict[str, Any]:
    exprs = program.get("exprs", [])
    defined: list[str] = []
    available: set[str] = set()
    inputs: list[str] = []
    for expr in exprs:
        for operand in (expr["lhs"], expr["rhs"]):
            if operand not in available:
                available.add(operand)
                inputs.append(operand)
        target = expr["target"]
        available.add(target)
        defined.append(target)
    return {
        "inputs": tuple(inputs),
        "defined_targets": tuple(defined),
        "available_symbols": tuple(available),
    }


__all__ = ["analyze_program", "eligibility_for", "export_program"]
