import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class MutationGuardStructuralTests(unittest.TestCase):
    def test_action_apply_transient_parent_assignment_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            const.parent = None
            const.parent = block

        action = CompilerAction("bad-parent-assignment", assign_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-parent-assignment").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("parent_assignment", violation["attempts"])
        self.assertIs(const.parent, block)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_results_assignment_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        original_results = const.results
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            const.results = ()
            const.results = original_results

        action = CompilerAction("bad-results-assignment", assign_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-results-assignment").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("results_assignment", violation["attempts"])
        self.assertIs(const.results, original_results)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_block_parent_assignment_is_rejected(self) -> None:
        block = Block()
        module_region = Region.from_block_list([block])
        module = builtin.module(module_region)
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            block.parent = None
            block.parent = module_region

        action = CompilerAction("bad-block-parent-assignment", assign_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-block-parent-assignment").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("block_parent_assignment", violation["attempts"])
        self.assertIs(block.parent, module_region)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_block_parent_assignment_is_rolled_back(self) -> None:
        block = Block()
        module_region = Region.from_block_list([block])
        module = builtin.module(module_region)
        run = PipelineRun(module)

        action = CompilerAction("bad-block-parent-clear", lambda current_run: setattr(block, "parent", None))

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertIs(block.parent, module_region)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_region_parent_assignment_is_rejected(self) -> None:
        block = Block()
        module_region = Region.from_block_list([block])
        module = builtin.module(module_region)
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            module_region.parent = None
            module_region.parent = module

        action = CompilerAction("bad-region-parent-assignment", assign_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-region-parent-assignment").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("region_parent_assignment", violation["attempts"])
        self.assertIs(module_region.parent, module)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_region_parent_assignment_is_rolled_back(self) -> None:
        block = Block()
        module_region = Region.from_block_list([block])
        module = builtin.module(module_region)
        run = PipelineRun(module)

        action = CompilerAction("bad-region-parent-clear", lambda current_run: setattr(module_region, "parent", None))

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertIs(module_region.parent, module)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_results_assignment_is_rolled_back(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        original_results = const.results
        run = PipelineRun(module)

        action = CompilerAction("bad-results-clear", lambda current_run: setattr(const, "results", ()))

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertIs(const.results, original_results)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_regions_assignment_is_rolled_back(self) -> None:
        block = Block()
        module_region = Region.from_block_list([block])
        module = builtin.module(module_region)
        original_regions = module.regions
        run = PipelineRun(module)

        action = CompilerAction("bad-regions-clear", lambda current_run: setattr(module, "regions", ()))

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertIs(module.regions, original_regions)
        self.assertIs(module_region.parent, module)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_successors_assignment_is_rejected_and_rolled_back(self) -> None:
        block = Block()
        successor = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            op = builder.insert(Operation.create("test.branch", successors=(successor,)))
        original_successors = op.successors
        run = PipelineRun(module)

        action = CompilerAction("bad-successors-clear", lambda current_run: setattr(op, "successors", ()))

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertIs(op.successors, original_successors)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_transient_direct_mutation_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            lhs = builder.insert(arith.constant(7, i32))
            old_rhs = builder.insert(arith.constant(1, i32))
            new_rhs = builder.insert(arith.constant(2, i32))
            const = builder.insert(arith.constant(3, i32))
            add = builder.insert(arith.addi(lhs.results[0], old_rhs.results[0]))
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            add.replace_operand(1, new_rhs.results[0])
            add.replace_operand(1, old_rhs.results[0])
            const.properties["value"] = 4
            const.properties["value"] = 3

        action = CompilerAction("bad-transient-mutation", mutate_then_restore)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-transient-mutation").value
        self.assertEqual(violation["kind"], "mutation_attempt")
        self.assertIn("replace_operand", violation["attempts"])
        self.assertIn("metadata_update", violation["attempts"])
        self.assertIs(add.operands[1], old_rhs.results[0])
        self.assertEqual(const.properties["value"], 3)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_direct_inserted_operation_is_detached_after_rejected_action_rollback(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        inserted = arith.constant(9, i32)
        run = PipelineRun(module)

        def insert_directly(current_run):
            with Builder().insert_at_end(block) as builder:
                builder.insert(inserted)

        action = CompilerAction("bad-direct-insert", insert_directly)

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertEqual(block.operations, ())
        self.assertIsNone(inserted.parent)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_direct_inserted_block_is_detached_after_rejected_action_rollback(self) -> None:
        original_block = Block()
        new_block = Block()
        region = Region.from_block_list([original_block])
        module = builtin.module(region)
        run = PipelineRun(module)

        action = CompilerAction(
            "bad-direct-block-insert",
            lambda current_run: region.append_block(new_block),
        )

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertEqual(region.blocks, (original_block,))
        self.assertIsNone(new_block.parent)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)


if __name__ == "__main__":
    unittest.main()
