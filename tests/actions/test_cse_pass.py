import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class CSEPassTests(unittest.TestCase):
    def test_cse_records_duplicate_erase_intent(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)

        intent = run.db.require("MutationIntent", duplicate.id).value
        self.assertEqual(intent.kind, "replace_uses_and_erase")

    def test_cse_does_not_merge_affine_apply_with_different_maps(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        first_map = affine.AffineMap(1, 0, ("d0",))
        second_map = affine.AffineMap(1, 0, ("d0 + 1",))
        with Builder().insert_at_end(block) as builder:
            dim = builder.insert(arith.constant(3, index)).results[0]
            first_apply = builder.insert(affine.apply(first_map, (dim,), ()))
            second_apply = builder.insert(affine.apply(second_map, (dim,), ()))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)

        self.assertEqual(run.db.query("MutationIntent", first_apply.id), ())
        self.assertEqual(run.db.query("MutationIntent", second_apply.id), ())

    def test_cse_merges_affine_apply_with_same_map_and_operands(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        map_ = affine.AffineMap(1, 0, ("d0 + 1",))
        with Builder().insert_at_end(block) as builder:
            dim = builder.insert(arith.constant(3, index)).results[0]
            representative = builder.insert(affine.apply(map_, (dim,), ()))
            duplicate = builder.insert(affine.apply(map_, (dim,), ()))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)

        intent = run.db.require("MutationIntent", duplicate.id).value
        self.assertEqual(intent.kind, "replace_uses_and_erase")
        self.assertIs(intent.replacement, representative.results[0])

    def test_cse_records_memory_read_evidence_for_affine_load_without_erasing_it(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        memref_type = memref.MemRefType(i32, (None,))
        mem = Operation.create("test.arg", result_types=(memref_type,)).results[0]
        map_ = affine.AffineMap(1, 0, ("d0",))
        with Builder().insert_at_end(block) as builder:
            idx = builder.insert(arith.constant(0, index))
            first_load = builder.insert(affine.load(mem, map_, dims=(idx.results[0],), symbols=()))
            second_load = builder.insert(affine.load(mem, map_, dims=(idx.results[0],), symbols=()))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)

        self.assertEqual(run.db.require("MemoryEffect", first_load.id).value["kind"], "read")
        self.assertEqual(run.db.require("MemoryEffect", second_load.id).value["kind"], "read")
        self.assertEqual(run.db.require("CSEMemoryEffect", first_load.id).value["action"], "read-observed")
        self.assertEqual(run.db.require("CSEMemoryEffect", second_load.id).value["action"], "read-observed")
        self.assertEqual(run.db.query("MutationIntent"), ())

    def test_cse_skips_memory_writing_ops_with_side_effect_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        memref_type = memref.MemRefType(i32, (None,))
        mem = Operation.create("test.arg", result_types=(memref_type,)).results[0]
        map_ = affine.AffineMap(1, 0, ("d0",))
        with Builder().insert_at_end(block) as builder:
            idx = builder.insert(arith.constant(0, index))
            value = builder.insert(arith.constant(7, i32))
            first_store = builder.insert(
                affine.store(value.results[0], mem, map_, dims=(idx.results[0],), symbols=())
            )
            second_store = builder.insert(
                affine.store(value.results[0], mem, map_, dims=(idx.results[0],), symbols=())
            )
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)

        self.assertEqual(run.db.require("MemoryEffect", first_store.id).value["kind"], "write")
        self.assertEqual(run.db.require("MemoryEffect", second_store.id).value["kind"], "write")
        self.assertEqual(run.db.require("CSEMemoryEffect", first_store.id).value["action"], "skip-side-effect")
        self.assertEqual(run.db.require("CSEMemoryEffect", second_store.id).value["action"], "skip-side-effect")
        self.assertEqual(run.db.query("MutationIntent"), ())

    def test_cse_replaces_duplicate_result_uses_before_erasing(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            representative = builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
            user = builder.insert(arith.addi(duplicate.results[0], representative.results[0]))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)
        intent = run.db.require("MutationIntent", duplicate.id).value

        self.assertEqual(intent.kind, "replace_uses_and_erase")
        self.assertIs(intent.replacement, representative.results[0])

        MutatorStage().run(run)

        self.assertNotIn(duplicate, block.operations)
        self.assertIs(user.operands[0], representative.results[0])
        self.assertEqual(duplicate.results[0].uses, ())
        self.assertTrue(
            any(use.owner is user and use.operand_index == 0 for use in representative.results[0].uses)
        )

    def test_cse_replacement_target_survives_symbol_dce_before_mutation(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            representative = builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
            two = builder.insert(arith.constant(2, i32))
            user = builder.insert(arith.addi(duplicate.results[0], two.results[0]))
            builder.insert(Operation.create("test.consume", operands=(user.results[0],)))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)
        passes.symbol_dce_and_dead_code().run(run)

        self.assertEqual(run.db.query("MutationIntent", representative.id), ())

        MutatorStage().run(run)

        self.assertIn(representative, block.operations)
        self.assertNotIn(duplicate, block.operations)
        self.assertIs(user.operands[0], representative.results[0])
        self.assertTrue(
            any(use.owner is user and use.operand_index == 0 for use in representative.results[0].uses)
        )


if __name__ == "__main__":
    unittest.main()
