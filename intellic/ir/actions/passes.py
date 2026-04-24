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
            key = _cse_key(op)
            if key is None:
                continue
            if key in seen:
                run.db.put("MatchRecord", op.id, MatchRecord("common-subexpression-elimination", op.id, "duplicate expression"))
                run.db.put("MutationIntent", op.id, MutationIntent("erase_op", op, reason="duplicate expression"))
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
    return CompilerAction("symbol-dce-and-dead-code", lambda run: None)


def inline_single_call() -> CompilerAction:
    return CompilerAction("inline-single-call", lambda run: None)


def loop_invariant_code_motion() -> CompilerAction:
    return CompilerAction("loop-invariant-code-motion", lambda run: None)


def lower_affine_to_scf() -> CompilerAction:
    def apply(run: PipelineRun) -> None:
        for op in _walk(run.module):
            if op.name in {"affine.load", "affine.store", "affine.vector_load", "affine.vector_store"}:
                record_affine_memory_effect(op, run.db)

    return CompilerAction("lower-affine-to-scf", apply)


def normalize_and_simplify_affine_loops() -> CompilerAction:
    return CompilerAction("normalize-and-simplify-affine-loops", lambda run: None)


def _record_replace(run: PipelineRun, action: str, op: Operation, replacement, reason: str) -> None:
    run.db.put("MatchRecord", op.id, MatchRecord(action, op.id, reason))
    run.db.put("MutationIntent", op.id, MutationIntent("replace_uses_and_erase", op, replacement, reason))


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
