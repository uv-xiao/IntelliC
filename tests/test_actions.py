import unittest

from intellic.ir.actions import MutatorStage, PendingRecordGate, PipelineRun, passes
from intellic.ir.dialects import arith, builtin
from intellic.ir.syntax import Block, Builder, Region, i32


class ActionTests(unittest.TestCase):
    def test_canonicalize_records_mutation_before_mutator_applies_it(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            value = builder.insert(arith.constant(7, i32))
            zero = builder.insert(arith.constant(0, i32))
            add = builder.insert(arith.addi(value.results[0], zero.results[0]))
        run = PipelineRun(module)

        passes.canonicalize_greedy().run(run)

        self.assertEqual(block.operations[-1], add)
        self.assertEqual(len(run.db.query("MutationIntent")), 1)
        with self.assertRaisesRegex(ValueError, "pending records"):
            PendingRecordGate().run(run)

        MutatorStage().run(run)

        self.assertNotIn(add, block.operations)
        self.assertEqual(len(run.db.query("MutationApplied")), 1)
        PendingRecordGate().run(run)

    def test_cse_records_duplicate_erase_intent(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)

        intent = run.db.require("MutationIntent", duplicate.id).value
        self.assertEqual(intent.kind, "erase_op")

    def test_constant_propagation_records_constant_facts(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(42, i32))
        run = PipelineRun(module)

        passes.sparse_constant_propagation().run(run)

        self.assertEqual(run.db.require("ValueConcrete", const.results[0].id).value, 42)

    def test_named_shared_passes_record_action_evidence(self) -> None:
        module = builtin.module(Region.from_block_list([Block()]))
        run = PipelineRun(module)

        for action in (
            passes.verify_structure(),
            passes.symbol_dce_and_dead_code(),
            passes.inline_single_call(),
            passes.loop_invariant_code_motion(),
            passes.lower_affine_to_scf(),
            passes.normalize_and_simplify_affine_loops(),
        ):
            action.run(run)

        action_names = [record.value["name"] for record in run.db.query("ActionRun")]
        self.assertIn("verify-structure", action_names)
        self.assertIn("inline-single-call", action_names)
        self.assertIn("lower-affine-to-scf", action_names)


if __name__ == "__main__":
    unittest.main()
