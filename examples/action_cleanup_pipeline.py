from __future__ import annotations

from dataclasses import dataclass

from examples.common import ExampleRun, print_example_run
from intellic.actions import passes
from intellic.dialects import arith, builtin, func
from intellic.ir.actions import MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.semantics import TraceDB, execute_function
from intellic.ir.syntax import Block, Builder, Region, i32, verify_operation
from intellic.ir.syntax.printer import print_operation


@dataclass(frozen=True)
class ActionCleanupPipelineExample:
    module: object
    main: object


def build_example() -> ActionCleanupPipelineExample:
    module_block = Block()
    module = builtin.module(Region.from_block_list([module_block]))
    unary_i32 = func.FunctionType(inputs=(i32,), results=(i32,))

    identity_block = Block(arg_types=(i32,))
    identity_region = Region.from_block_list([identity_block])
    with Builder().insert_at_end(identity_block) as builder:
        builder.insert(func.return_(identity_block.arguments[0]))
    identity = func.func("identity", unary_i32, identity_region)
    identity.properties["sym_visibility"] = "private"

    dead_block = Block(arg_types=(i32,))
    dead_region = Region.from_block_list([dead_block])
    with Builder().insert_at_end(dead_block) as builder:
        builder.insert(func.return_(dead_block.arguments[0]))
    dead_private = func.func("dead_private", unary_i32, dead_region)
    dead_private.properties["sym_visibility"] = "private"

    main_block = Block(arg_types=(i32,))
    main_region = Region.from_block_list([main_block])
    with Builder().insert_at_end(main_block) as builder:
        call = builder.insert(func.call("identity", (main_block.arguments[0],), unary_i32))
        zero = builder.insert(arith.constant(0, i32))
        cleaned = builder.insert(arith.addi(call.results[0], zero.results[0]))
        builder.insert(arith.constant(1, i32))
        duplicate_one = builder.insert(arith.constant(1, i32))
        result = builder.insert(arith.addi(cleaned.results[0], duplicate_one.results[0]))
        builder.insert(func.return_(result.results[0]))
    main = func.func("main", unary_i32, main_region)

    with Builder().insert_at_end(module_block) as builder:
        builder.insert(identity)
        builder.insert(dead_private)
        builder.insert(main)

    return ActionCleanupPipelineExample(module=module, main=main)


def run_demo() -> ExampleRun:
    example = build_example()
    verify_operation(example.module)

    canonical_ir = print_operation(example.module)
    parsed = parse_operation(canonical_ir)
    parse_print_idempotent = canonical_ir == print_operation(parsed)

    before_db = TraceDB()
    before_result = execute_function(example.main, (4,), before_db)
    if before_result != (5,):
        raise AssertionError(f"expected pre-pipeline result (5,), got {before_result}")

    run = PipelineRun(example.module)
    actions = (
        passes.verify_structure(),
        passes.canonicalize_greedy(),
        passes.common_subexpression_elimination(),
        passes.sparse_constant_propagation(),
        passes.symbol_dce_and_dead_code(),
        passes.inline_single_call(),
    )
    for action in actions:
        action.run(run)
    MutatorStage().run(run)
    passes.symbol_dce_and_dead_code().run(run)
    MutatorStage().run(run)
    PendingRecordGate().run(run)

    verify_operation(example.module)

    after_db = TraceDB()
    semantic_result = execute_function(example.main, (4,), after_db)
    if semantic_result != before_result:
        raise AssertionError(
            f"pipeline changed semantic result from {before_result} to {semantic_result}"
        )

    final_ir = print_operation(example.module)
    final_parsed = parse_operation(final_ir)
    final_parse_print_idempotent = final_ir == print_operation(final_parsed)

    relation_names = (
        "MutationApplied",
        "MutationRejected",
        "RewriteEvidence",
        "SymbolLiveness",
        "CallGraphEdge",
    )
    relation_counts = {
        name: len(run.db.query(name))
        for name in relation_names
    }
    semantic_records = {
        "before.Evaluated": len(before_db.query("Evaluated")),
        "before.Call": len(before_db.query("Call")),
        "after.Evaluated": len(after_db.query("Evaluated")),
        "after.Call": len(after_db.query("Call")),
    }
    action_names = tuple(record.value["name"] for record in run.db.query("ActionRun"))

    return ExampleRun(
        name="action_cleanup_pipeline",
        canonical_ir=canonical_ir,
        parse_print_idempotent=parse_print_idempotent and final_parse_print_idempotent,
        semantic_result=semantic_result,
        semantic_records=semantic_records,
        action_names=action_names,
        relation_counts=relation_counts,
        mutation_applied_count=relation_counts["MutationApplied"],
        mutation_rejected_count=relation_counts["MutationRejected"],
        final_ir=final_ir,
    )


def main() -> None:
    print(print_example_run(run_demo()), end="")


if __name__ == "__main__":
    main()
