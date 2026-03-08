from __future__ import annotations

import re
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


def import_program_from_module(
    module_text: str, ledger: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed = _parse_module(module_text)
    ledger_by_result = {
        str(item["mlir_result"]): dict(item)
        for item in ledger.get("ops", ())
        if isinstance(item, Mapping) and isinstance(item.get("mlir_result"), str)
    }
    args = tuple(parsed["args"])
    available_symbols = {f"%{name}": name for name in args}
    imported_exprs: list[dict[str, Any]] = []
    surviving_targets: dict[str, str] = {}
    for op in parsed["ops"]:
        result_name = str(op["result"])
        entry = ledger_by_result.get(result_name)
        if entry is None:
            raise ValueError(f"unknown SSA value mapping for {result_name}")
        lhs_symbol = available_symbols.get(str(op["lhs"]))
        rhs_symbol = available_symbols.get(str(op["rhs"]))
        if lhs_symbol is None or rhs_symbol is None:
            raise ValueError("unknown SSA value referenced by transformed MLIR operand")
        imported_expr = {
            "target": str(entry["target"]),
            "op": str(entry["op"]),
            "lhs": lhs_symbol,
            "rhs": rhs_symbol,
        }
        imported_exprs.append(imported_expr)
        available_symbols[result_name] = imported_expr["target"]
        surviving_targets[result_name] = imported_expr["target"]

    result_symbol = available_symbols.get(str(parsed["return"]))
    if result_symbol is None:
        raise ValueError("unknown SSA value returned by transformed MLIR module")

    surviving_signatures = {
        (str(item["op"]), str(item["lhs"]), str(item["rhs"])): surviving_targets[str(item["mlir_result"])]
        for item in ledger.get("ops", ())
        if isinstance(item, Mapping) and str(item.get("mlir_result")) in surviving_targets
    }
    rewrites = []
    for item in ledger.get("ops", ()):
        if not isinstance(item, Mapping):
            continue
        result_name = str(item.get("mlir_result"))
        if result_name in surviving_targets:
            continue
        signature = (str(item["op"]), str(item["lhs"]), str(item["rhs"]))
        reused_target = surviving_signatures.get(signature)
        if reused_target is None:
            continue
        rewrites.append(
            {
                "eliminated_target": str(item["target"]),
                "reused_target": reused_target,
                "signature": f"{item['op']}({item['lhs']}, {item['rhs']})",
            }
        )

    imported_program = {
        "entry": str(parsed["entry"]),
        "exprs": imported_exprs,
        "inputs": args,
        "result": result_symbol,
    }
    return imported_program, {
        "schema": "htp_ext.mlir_cse.import_summary.v1",
        "entry": str(parsed["entry"]),
        "rewrites": rewrites,
        "result": result_symbol,
    }


_FUNC_RE = re.compile(r"func\.func\s+@(?P<entry>[A-Za-z_][\w]*)\((?P<args>[^)]*)\)\s*->\s*i32\s*\{")
_OP_RE = re.compile(
    r"(?P<result>%[A-Za-z_][\w]*)\s*=\s*(?P<op>arith\.(?:addi|muli))\s+"
    r"(?P<lhs>%[A-Za-z_][\w]*),\s*(?P<rhs>%[A-Za-z_][\w]*)\s*:\s*i32"
)
_RETURN_RE = re.compile(r"return\s+(?P<value>%[A-Za-z_][\w]*)\s*:\s*i32")


def _parse_module(module_text: str) -> dict[str, Any]:
    entry: str | None = None
    args: list[str] = []
    ops: list[dict[str, str]] = []
    defined: set[str] = set()
    return_value: str | None = None

    for raw_line in module_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if entry is None:
            match = _FUNC_RE.search(line)
            if match:
                entry = match.group("entry")
                args_text = match.group("args").strip()
                if args_text:
                    args = [segment.split(":")[0].strip().lstrip("%") for segment in args_text.split(",")]
                    defined.update(f"%{name}" for name in args)
                continue
        op_match = _OP_RE.fullmatch(line)
        if op_match:
            lhs = op_match.group("lhs")
            rhs = op_match.group("rhs")
            if lhs not in defined or rhs not in defined:
                raise ValueError("unknown SSA value referenced by transformed MLIR operand")
            result_name = op_match.group("result")
            ops.append(
                {
                    "result": result_name,
                    "op": "add" if op_match.group("op") == "arith.addi" else "mul",
                    "lhs": lhs,
                    "rhs": rhs,
                }
            )
            defined.add(result_name)
            continue
        return_match = _RETURN_RE.fullmatch(line)
        if return_match:
            return_value = return_match.group("value")
            if return_value not in defined:
                raise ValueError("unknown SSA value returned by transformed MLIR module")
    if entry is None:
        raise ValueError("missing MLIR function definition")
    if return_value is None:
        raise ValueError("missing MLIR return")
    return {"entry": entry, "args": tuple(args), "ops": ops, "return": return_value}


__all__ = ["import_program", "import_program_from_module"]
