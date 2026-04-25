from dataclasses import dataclass

from examples.common import ExampleRun, print_example_run
from intellic.actions import passes
from intellic.ir.actions import MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.semantics import TraceDB, execute_function
from intellic.ir.syntax import Value, i32, index
from intellic.ir.syntax.printer import print_operation
from intellic.surfaces.api import arith, func, scf


@dataclass(frozen=True)
class SumToNExample:
    operation: object
    evidence: tuple[str, ...]
    zero_i: Value


def build_sum_to_n() -> SumToNExample:
    captures: dict[str, Value] = {}

    @func.ir_function
    def sum_to_n(n: index) -> i32:
        zero_i = arith.constant(0, index)
        one_i = arith.constant(1, index)
        zero = arith.constant(0, i32)
        captures["zero_i"] = zero_i

        with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
            i, total = loop.arguments
            total_next = arith.addi(total, arith.index_cast(i, i32))
            scf.yield_(total_next)

        return loop.results[0]

    return SumToNExample(sum_to_n.operation, sum_to_n.evidence, captures["zero_i"])


def run_demo() -> ExampleRun:
    example = build_sum_to_n()
    canonical_ir = print_operation(example.operation)
    parsed = parse_operation(canonical_ir)
    parse_print_idempotent = canonical_ir == print_operation(parsed)

    semantic_db = TraceDB()
    semantic_result = execute_function(example.operation, (5,), semantic_db)

    run = PipelineRun(example.operation)
    for action in (
        passes.verify_structure(),
        passes.canonicalize_greedy(),
        passes.common_subexpression_elimination(),
        passes.sparse_constant_propagation(),
        passes.symbol_dce_and_dead_code(),
        passes.inline_single_call(),
        passes.loop_invariant_code_motion(),
        passes.normalize_and_simplify_affine_loops(),
    ):
        action.run(run)
    MutatorStage().run(run)
    PendingRecordGate().run(run)

    relation_counts = {
        "ValueConcrete": len(run.db.query("ValueConcrete")),
        "LoopInvariantCandidate": len(run.db.query("LoopInvariantCandidate")),
        "MutationApplied": len(run.db.query("MutationApplied")),
        "MutationRejected": len(run.db.query("MutationRejected")),
    }
    semantic_records = {
        "Call": len(semantic_db.query("Call")),
        "Evaluated": len(semantic_db.query("Evaluated")),
        "LoopIteration": len(semantic_db.query("LoopIteration")),
    }
    action_names = tuple(record.value["name"] for record in run.db.query("ActionRun"))

    return ExampleRun(
        name="sum_to_n",
        canonical_ir=canonical_ir,
        parse_print_idempotent=parse_print_idempotent,
        semantic_result=semantic_result,
        semantic_records=semantic_records,
        action_names=action_names,
        relation_counts=relation_counts,
        mutation_applied_count=relation_counts["MutationApplied"],
        mutation_rejected_count=relation_counts["MutationRejected"],
    )


def main() -> None:
    print(print_example_run(run_demo()), end="")


if __name__ == "__main__":
    main()
