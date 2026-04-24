from __future__ import annotations

from intellic.ir.semantics.builtin import record_affine_memory_effect
from intellic.ir.syntax import Operation, verify_operation

from .action import CompilerAction
from .match import MatchRecord
from .mutation import MutationIntent
from .pipeline import PipelineRun


def verify_structure() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        verify_operation(run.module)

    return CompilerAction("verify-structure", apply)


def canonicalize_greedy() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        for op in _walk(run.module):
            if op.name == "arith.addi":
                lhs, rhs = op.operands
                if _constant_value(lhs) == 0:
                    _record_replace(run, "canonicalize-greedy", op, rhs, "fold add-zero lhs")
                elif _constant_value(rhs) == 0:
                    _record_replace(run, "canonicalize-greedy", op, lhs, "fold add-zero rhs")

    return CompilerAction("canonicalize-greedy", apply)


def common_subexpression_elimination() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        seen: dict[tuple, Operation] = {}
        for op in _walk(run.module):
            memory_effect = _cse_memory_effect(op, run)
            if memory_effect == "write":
                continue
            if memory_effect == "read":
                continue
            key = _cse_key(op)
            if key is None:
                continue
            if key in seen:
                run.db.put("MatchRecord", op.id, MatchRecord("common-subexpression-elimination", op.id, "duplicate expression"))
                representative = seen[key]
                if len(op.results) == 1 and len(representative.results) == 1:
                    run.db.put(
                        "MutationIntent",
                        op.id,
                        MutationIntent(
                            "replace_uses_and_erase",
                            op,
                            representative.results[0],
                            "duplicate expression",
                        ),
                    )
                    run.db.put(
                        "RewriteEvidence",
                        op.id,
                        {
                            "action": "common-subexpression-elimination",
                            "representative": representative.id,
                            "replaced_results": (op.results[0].id,),
                        },
                    )
            else:
                seen[key] = op

    return CompilerAction("common-subexpression-elimination", apply)


def sparse_constant_propagation() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        for op in _walk(run.module):
            if op.name == "arith.constant":
                run.db.put("ValueConcrete", op.results[0].id, op.properties["value"])

    return CompilerAction("sparse-constant-propagation", apply)


def symbol_dce_and_dead_code() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        live_symbols = _called_symbols(run.module) | {"main"}
        pending_replacement_targets = _pending_replacement_target_ids(run)
        for op in _walk(run.module):
            if op.name == "func.func":
                symbol = op.properties.get("sym_name")
                is_live = symbol in live_symbols
                run.db.put(
                    "SymbolLiveness",
                    op.id,
                    {"symbol": symbol, "live": is_live, "reason": "callgraph-root" if is_live else "unreferenced"},
                )
                if not is_live:
                    run.db.put(
                        "DeadCodeCandidate",
                        op.id,
                        {
                            "reason": "unused function",
                            "symbol": symbol,
                            "mutation": "erase" if _is_private_symbol(op) else "skipped without visibility contract",
                        },
                    )
                    if _is_private_symbol(op):
                        run.db.put("MutationIntent", op.id, MutationIntent("erase_op", op, reason="unused private function"))
            elif any(result.id in pending_replacement_targets for result in op.results):
                run.db.put("Liveness", op.id, {"live": True, "reason": "pending replacement target"})
            elif _is_unused_pure_op(op):
                run.db.put("Liveness", op.id, {"live": False, "reason": "all results unused"})
                run.db.put("DeadCodeCandidate", op.id, {"reason": "unused pure op"})
                run.db.put("MutationIntent", op.id, MutationIntent("erase_op", op, reason="unused pure op"))

    return CompilerAction("symbol-dce-and-dead-code", apply)


def inline_single_call() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        functions = _functions_by_symbol(run.module)
        call_counts = _call_counts(run.module)
        for call in _walk(run.module):
            if call.name != "func.call":
                continue
            callee_name = call.properties.get("callee")
            callee = functions.get(callee_name)
            if callee is None:
                continue
            edge = {
                "caller": _containing_function(call).id if _containing_function(call) is not None else None,
                "callee": callee.id,
                "callee_name": callee_name,
                "args": tuple(operand.id for operand in call.operands),
                "results": tuple(result.id for result in call.results),
            }
            run.db.put("CallGraphEdge", call.id, edge)
            mapping = _single_return_forward_mapping(callee, call)
            if call_counts.get(callee_name, 0) == 1 and mapping is not None:
                run.db.put("MatchRecord", call.id, MatchRecord("inline-single-call", call.id, "single direct call"))
                run.db.put(
                    "InlineIntent",
                    call.id,
                    {
                        "callee": callee.id,
                        "strategy": "single-return-forward",
                        "result_replacements": tuple(value.id for value in mapping),
                    },
                )
                if len(call.results) == 1 and len(mapping) == 1:
                    run.db.put(
                        "MutationIntent",
                        call.id,
                        MutationIntent(
                            "replace_uses_and_erase",
                            call,
                            mapping[0],
                            "single-call inline return forwarding",
                        ),
                    )
                    run.db.put(
                        "RewriteEvidence",
                        call.id,
                        {
                            "action": "inline-single-call",
                            "callee": callee.id,
                            "boundary": "single-result block-argument forwarding",
                        },
                    )

    return CompilerAction("inline-single-call", apply)


def loop_invariant_code_motion() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        for loop in _walk(run.module):
            if loop.name not in {"scf.for", "affine.for"}:
                continue
            run.db.put(
                "LoopScope",
                loop.id,
                {
                    "kind": loop.name,
                    "operands": tuple(operand.id for operand in loop.operands),
                    "regions": tuple(region.id for region in loop.regions),
                },
            )
            for op in _region_ops(loop):
                if _is_loop_invariant(loop, op):
                    run.db.put(
                        "LoopInvariantCandidate",
                        op.id,
                        {
                            "loop": loop.id,
                            "action": "would_move_before_loop",
                            "reason": "pure op operands defined outside loop",
                        },
                    )
                    run.db.put(
                        "RewriteEvidence",
                        op.id,
                        {
                            "action": "loop-invariant-code-motion",
                            "loop": loop.id,
                            "boundary": "record-only first slice",
                        },
                    )

    return CompilerAction("loop-invariant-code-motion", apply)


def lower_affine_to_scf() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        for op in _walk(run.module):
            if op.name in {"affine.apply", "affine.min", "affine.max"}:
                _record_affine_expansion(op, run)
            if op.name in {"affine.load", "affine.store", "affine.vector_load", "affine.vector_store"}:
                _record_affine_expansion(op, run)
                record_affine_memory_effect(op, run.db)

    return CompilerAction("lower-affine-to-scf", apply)


def normalize_and_simplify_affine_loops() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        for op in _walk(run.module):
            if op.name != "affine.for":
                continue
            lower_map = op.properties["lower_map"]
            upper_map = op.properties["upper_map"]
            bounds = {
                "lower_map": lower_map,
                "upper_map": upper_map,
                "lower_operands": tuple(operand.id for operand in op.operands),
                "upper_operands": tuple(operand.id for operand in op.operands),
                "step": op.properties["step"],
                "scope": tuple(region.id for region in op.regions),
            }
            run.db.put("AffineLoopBounds", op.id, bounds)
            run.db.put(
                "AffineLoopBand",
                op.id,
                {"loops": (op.id,), "ivs": (), "bounds": (bounds,), "permutable": True},
            )
            run.db.put(
                "AffineNormalizedBounds",
                op.id,
                {
                    "lower": lower_map.results,
                    "upper": upper_map.results,
                    "step": op.properties["step"],
                    "evidence": "first-slice affine.for bound normalization",
                },
            )

    return CompilerAction("normalize-and-simplify-affine-loops", apply)


def _record_replace(run: PipelineRun, action: str, op: Operation, replacement, reason: str) -> None:
    run.db.put("MatchRecord", op.id, MatchRecord(action, op.id, reason))
    run.db.put("MutationIntent", op.id, MutationIntent("replace_uses_and_erase", op, replacement, reason))
    run.db.put(
        "RewriteEvidence",
        op.id,
        {
            "action": action,
            "replacement": replacement.id,
            "reason": reason,
        },
    )


def _walk(op: Operation) -> tuple[Operation, ...]:
    found = [op]
    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                found.extend(_walk(child))
    return tuple(found)


def _constant_value(value) -> object | None:
    owner = getattr(value, "owner", None)
    if isinstance(owner, Operation) and owner.name == "arith.constant":
        return owner.properties["value"]
    return None


def _cse_key(op: Operation) -> tuple | None:
    if op.name == "arith.constant":
        return (op.name, op.properties["value"], tuple(result.type for result in op.results))
    if op.name in {"arith.addi", "arith.index_cast", "affine.apply"}:
        return (op.name, tuple(id(operand) for operand in op.operands), tuple(result.type for result in op.results))
    return None


def _cse_memory_effect(op: Operation, run: PipelineRun) -> str | None:
    if op.name not in {"affine.load", "affine.store", "affine.vector_load", "affine.vector_store"}:
        return None
    record_affine_memory_effect(op, run.db)
    effect = "read" if op.name in {"affine.load", "affine.vector_load"} else "write"
    run.db.put(
        "CSEMemoryEffect",
        op.id,
        {
            "effect": effect,
            "action": "read-observed" if effect == "read" else "skip-side-effect",
            "reason": "memory read requires alias/order proof" if effect == "read" else "memory write has side effects",
        },
    )
    return effect


def _called_symbols(root: Operation) -> set[object]:
    return {
        op.properties.get("callee")
        for op in _walk(root)
        if op.name == "func.call"
    }


def _functions_by_symbol(root: Operation) -> dict[object, Operation]:
    return {
        op.properties.get("sym_name"): op
        for op in _walk(root)
        if op.name == "func.func"
    }


def _call_counts(root: Operation) -> dict[object, int]:
    counts: dict[object, int] = {}
    for op in _walk(root):
        if op.name == "func.call":
            callee = op.properties.get("callee")
            counts[callee] = counts.get(callee, 0) + 1
    return counts


def _containing_function(op: Operation) -> Operation | None:
    current = op.parent
    while current is not None:
        if isinstance(current, Operation) and current.name == "func.func":
            return current
        current = getattr(current, "parent", None)
    return None


def _single_return_forward_mapping(callee: Operation, call: Operation):
    if not callee.regions or len(callee.regions[0].blocks) != 1:
        return None
    block = callee.regions[0].blocks[0]
    if not block.operations or block.operations[-1].name != "func.return":
        return None
    terminator = block.operations[-1]
    replacements = []
    for returned in terminator.operands:
        owner = getattr(returned, "owner", None)
        index = getattr(returned, "index", None)
        if owner is block and index is not None and index < len(call.operands):
            replacements.append(call.operands[index])
        else:
            return None
    if len(replacements) != len(call.results):
        return None
    return tuple(replacements)


def _is_unused_pure_op(op: Operation) -> bool:
    if op.parent is None or not _is_pure_op(op):
        return False
    return bool(op.results) and all(not result.uses for result in op.results)


def _pending_replacement_target_ids(run: PipelineRun) -> set[object]:
    target_ids = set()
    for record in run.db.query("MutationIntent"):
        intent = record.value
        if isinstance(intent, MutationIntent) and intent.kind == "replace_uses_and_erase" and intent.replacement is not None:
            target_ids.add(intent.replacement.id)
    return target_ids


def _is_private_symbol(op: Operation) -> bool:
    return op.properties.get("sym_visibility") == "private" or op.properties.get("visibility") == "private"


def _is_pure_op(op: Operation) -> bool:
    return op.name in {
        "arith.constant",
        "arith.addi",
        "arith.index_cast",
        "affine.apply",
        "affine.min",
        "affine.max",
    }


def _region_ops(op: Operation) -> tuple[Operation, ...]:
    found: list[Operation] = []
    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                found.extend(_walk(child))
    return tuple(found)


def _is_loop_invariant(loop: Operation, op: Operation) -> bool:
    if not _is_pure_op(op):
        return False
    region_op_ids = {region_op.id for region_op in _region_ops(loop)}
    for operand in op.operands:
        owner = getattr(operand, "owner", None)
        if isinstance(owner, Operation) and owner.id in region_op_ids:
            return False
        if owner in {block for region in loop.regions for block in region.blocks}:
            return False
    return True


def _record_affine_expansion(op: Operation, run: PipelineRun) -> None:
    map_ = op.properties.get("map")
    if map_ is None:
        return
    dim_count = op.properties.get("dim_count", getattr(map_, "dim_count", 0))
    symbol_count = op.properties.get("symbol_count", getattr(map_, "symbol_count", 0))
    operands = op.operands
    memory_prefix = 0
    if op.name in {"affine.load", "affine.vector_load"}:
        memory_prefix = 1
    elif op.name in {"affine.store", "affine.vector_store"}:
        memory_prefix = 2
    dims = operands[memory_prefix:memory_prefix + dim_count]
    symbols = operands[memory_prefix + dim_count:memory_prefix + dim_count + symbol_count]
    run.db.put(
        "AffineDimSymbolMapping",
        op.id,
        {
            "dims": tuple(value.id for value in dims),
            "symbols": tuple(value.id for value in symbols),
            "dim_count": dim_count,
            "symbol_count": symbol_count,
        },
    )
    run.db.put(
        "AffineExpansion",
        op.id,
        {
            "map": map_,
            "results": getattr(map_, "results", ()),
            "target": "scf-index-arithmetic",
            "evidence": "first-slice affine expansion mapping",
        },
    )
