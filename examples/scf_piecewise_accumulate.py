from dataclasses import dataclass

from examples.common import ExampleRun, print_example_run
from intellic.actions import passes
from intellic.dialects import arith as arith_dialect
from intellic.dialects import scf as scf_dialect
from intellic.ir.actions import PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import Block, Builder, Region, i1, i32, index, verify_operation
from intellic.ir.syntax.printer import print_operation
from intellic.surfaces.api import arith, builders, func, scf


@dataclass(frozen=True)
class ScfPiecewiseAccumulateExample:
    operation: object


def build_example() -> ScfPiecewiseAccumulateExample:
    @func.ir_function
    def scf_piecewise_accumulate(n: index) -> i32:
        zero_i = arith.constant(0, index)
        one_i = arith.constant(1, index)
        zero = arith.constant(0, i32)

        with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
            iv, total = loop.arguments
            cond = arith.constant(1, i1)
            iv_i32 = arith.index_cast(iv, i32)

            then_block = Block()
            then_region = Region.from_block_list([then_block])
            with Builder().insert_at_end(then_block) as builder:
                updated = builder.insert(arith_dialect.addi(total, iv_i32))
                builder.insert(scf_dialect.yield_(updated.results[0]))

            else_block = Block()
            else_region = Region.from_block_list([else_block])
            with Builder().insert_at_end(else_block) as builder:
                builder.insert(scf_dialect.yield_(total))

            if_op = builders.emit(
                scf_dialect.if_(
                    cond,
                    then_region=then_region,
                    else_region=else_region,
                    result_types=(i32,),
                ),
                "builder:scf.if",
            )
            scf.yield_(if_op.results[0])

        return loop.results[0]

    return ScfPiecewiseAccumulateExample(operation=scf_piecewise_accumulate.operation)


def run_demo() -> ExampleRun:
    example = build_example()
    verify_operation(example.operation)
    canonical_ir = print_operation(example.operation)
    parse_print_idempotent = canonical_ir == print_operation(parse_operation(canonical_ir))

    run = PipelineRun(example.operation)
    for action in (
        passes.verify_structure(),
        passes.sparse_constant_propagation(),
        passes.loop_invariant_code_motion(),
    ):
        action.run(run)

    return ExampleRun(
        name="scf_piecewise_accumulate",
        canonical_ir=canonical_ir,
        parse_print_idempotent=parse_print_idempotent,
        action_names=tuple(record.value["name"] for record in run.db.query("ActionRun")),
        relation_counts={
            "BranchReachability": len(run.db.query("BranchReachability")),
            "LoopInvariantCandidate": len(run.db.query("LoopInvariantCandidate")),
        },
        documented_gaps=("scf.if concrete execution is not implemented",),
    )


def main() -> None:
    print(print_example_run(run_demo()), end="")


if __name__ == "__main__":
    main()
