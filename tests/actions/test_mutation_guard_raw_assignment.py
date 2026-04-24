import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class MutationGuardRawAssignmentTests(unittest.TestCase):
    def test_action_apply_transient_raw_operand_assignment_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            lhs = builder.insert(arith.constant(7, i32))
            old_rhs = builder.insert(arith.constant(1, i32))
            new_rhs = builder.insert(arith.constant(2, i32))
            add = builder.insert(arith.addi(lhs.results[0], old_rhs.results[0]))
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            add.operands = (lhs.results[0], new_rhs.results[0])
            add.operands = (lhs.results[0], old_rhs.results[0])

        action = CompilerAction("bad-raw-operand-assignment", mutate_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-raw-operand-assignment").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("operand_assignment", violation["attempts"])
        self.assertIs(add.operands[1], old_rhs.results[0])
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_raw_block_reorder_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            first = builder.insert(arith.constant(1, i32))
            second = builder.insert(arith.constant(2, i32))
        run = PipelineRun(module)

        def reorder_then_restore(current_run):
            block._operations.reverse()
            block._operations.reverse()

        action = CompilerAction("bad-raw-block-reorder", reorder_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-raw-block-reorder").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("block_operations_reorder", violation["attempts"])
        self.assertEqual(block.operations, (first, second))
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_raw_region_block_reorder_is_rejected(self) -> None:
        first_block = Block()
        second_block = Block()
        region = Region.from_block_list([first_block, second_block])
        module = builtin.module(region)
        run = PipelineRun(module)

        action = CompilerAction(
            "bad-region-block-reorder",
            lambda current_run: region._blocks.reverse(),
        )

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-region-block-reorder").value
        self.assertEqual(violation["kind"], "region_blocks_changed")
        self.assertEqual(region.blocks, (first_block, second_block))
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_raw_region_block_reorder_is_rejected(self) -> None:
        first_block = Block()
        second_block = Block()
        region = Region.from_block_list([first_block, second_block])
        module = builtin.module(region)
        run = PipelineRun(module)

        def reorder_then_restore(current_run):
            region._blocks.reverse()
            region._blocks.reverse()

        action = CompilerAction("bad-transient-region-block-reorder", reorder_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-transient-region-block-reorder").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("region_blocks_reorder", violation["attempts"])
        self.assertEqual(region.blocks, (first_block, second_block))
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_raw_properties_assignment_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        original = const.properties
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            const.properties = {"value": 8}
            const.properties = original

        action = CompilerAction("bad-raw-properties-assignment", assign_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-raw-properties-assignment").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("metadata_assignment", violation["attempts"])
        self.assertEqual(const.properties["value"], 7)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_raw_attributes_assignment_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            op = builder.insert(
                Operation.create(
                    "test.with_attr",
                    attributes={"tag": Attribute("tag", "before")},
                )
            )
        original = op.attributes
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            op.attributes = {"tag": Attribute("tag", "after")}
            op.attributes = original

        action = CompilerAction("bad-raw-attributes-assignment", assign_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-raw-attributes-assignment").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("metadata_assignment", violation["attempts"])
        self.assertEqual(op.attributes["tag"], Attribute("tag", "before"))
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)


if __name__ == "__main__":
    unittest.main()
