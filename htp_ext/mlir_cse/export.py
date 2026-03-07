from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from htp.passes.program_model import canonicalize_program


def eligibility_for(program: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_expr_program(program)
    exprs = normalized.get("exprs")
    reasons: list[str] = []
    ok = isinstance(normalized.get("entry"), str) and isinstance(exprs, list)
    result = normalized.get("result")
    if not ok:
        reasons.append(
            "program requires a string entry and a list of exprs or a canonical scalar elementwise kernel"
        )
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
        "entry": normalized.get("entry"),
        "result": result,
        "reasons": reasons,
    }


def export_program(program: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    normalized = normalize_expr_program(program)
    analysis = analyze_program(normalized)
    exprs = normalized.get("exprs", [])
    arguments = ", ".join(f"%{name}: i32" for name in analysis["inputs"])
    lines = [
        "module {",
        f"  func.func @{normalized['entry']}({arguments}) -> i32 {{",
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
                "entity_id": f"{normalized['entry']}:E{index}",
            }
        )
    lines.append(f"    return {value_names[normalized['result']]} : i32")
    lines.append("  }")
    lines.append("}")
    ledger = {
        "schema": "htp_ext.mlir_cse.ledger.v1",
        "entry": normalized["entry"],
        "inputs": analysis["inputs"],
        "result": normalized["result"],
        "ops": ledger_ops,
    }
    return "\n".join(lines) + "\n", ledger


def analyze_program(program: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_expr_program(program)
    exprs = normalized.get("exprs", [])
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


def normalize_expr_program(program: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(program.get("exprs"), list):
        return dict(program)
    canonical = canonicalize_program(program)
    kernel = canonical["kernel"]
    exprs: list[dict[str, Any]] = []
    result: str | None = None
    for op in kernel.get("ops", ()):
        if str(op.get("op")) != "elementwise_binary" or str(op.get("dtype")) != "i32":
            return dict(program)
        if str(op.get("operator")) not in {"add", "mul"}:
            return dict(program)
        if op.get("shape") not in ([], ()):
            return dict(program)
        exprs.append(
            {
                "target": str(op["out"]),
                "op": str(op["operator"]),
                "lhs": str(op["lhs"]),
                "rhs": str(op["rhs"]),
            }
        )
        result = str(op["out"])
    normalized = {
        "entry": str(canonical["entry"]),
        "exprs": exprs,
        "result": str(program.get("result", result or "")),
    }
    return normalized


__all__ = ["analyze_program", "eligibility_for", "export_program", "normalize_expr_program"]
