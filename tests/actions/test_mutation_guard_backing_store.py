import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class MutationGuardBackingStoreTests(unittest.TestCase):
    def test_action_apply_base_dict_metadata_mutator_cannot_silently_pass(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            dict.__setitem__(const.properties, "value", 8)
            dict.__setitem__(const.properties, "value", 7)

        action = CompilerAction("bad-base-dict-mutation", mutate_then_restore)

        with self.assertRaises((TypeError, ValueError)):
            action.run(run)

        self.assertEqual(const.properties["value"], 7)

    def test_action_apply_base_list_block_mutator_cannot_silently_pass(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            first = builder.insert(arith.constant(1, i32))
            second = builder.insert(arith.constant(2, i32))
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            list.reverse(block._operations)
            list.reverse(block._operations)

        action = CompilerAction("bad-base-list-block-mutation", mutate_then_restore)

        with self.assertRaises((TypeError, ValueError)):
            action.run(run)

        self.assertEqual(block.operations, (first, second))

    def test_action_apply_base_list_region_mutator_cannot_silently_pass(self) -> None:
        first_block = Block()
        second_block = Block()
        region = Region.from_block_list([first_block, second_block])
        module = builtin.module(region)
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            list.reverse(region._blocks)
            list.reverse(region._blocks)

        action = CompilerAction("bad-base-list-region-mutation", mutate_then_restore)

        with self.assertRaises((TypeError, ValueError)):
            action.run(run)

        self.assertEqual(region.blocks, (first_block, second_block))

    def test_action_apply_metadata_backing_store_mutator_cannot_silently_pass(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            const.properties._data["value"] = 8
            const.properties._data["value"] = 7

        action = CompilerAction("bad-metadata-backing-mutation", mutate_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertEqual(const.properties["value"], 7)

    def test_action_apply_block_operations_backing_store_mutator_cannot_silently_pass(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            first = builder.insert(arith.constant(1, i32))
            second = builder.insert(arith.constant(2, i32))
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            block._operations._data.reverse()
            block._operations._data.reverse()

        action = CompilerAction("bad-block-backing-mutation", mutate_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertEqual(block.operations, (first, second))

    def test_action_apply_region_blocks_backing_store_mutator_cannot_silently_pass(self) -> None:
        first_block = Block()
        second_block = Block()
        region = Region.from_block_list([first_block, second_block])
        module = builtin.module(region)
        run = PipelineRun(module)

        def mutate_then_restore(current_run):
            region._blocks._data.reverse()
            region._blocks._data.reverse()

        action = CompilerAction("bad-region-backing-mutation", mutate_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertEqual(region.blocks, (first_block, second_block))

    def test_action_apply_raw_object_operands_reassignment_cannot_silently_pass(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            lhs = builder.insert(arith.constant(7, i32))
            old_rhs = builder.insert(arith.constant(1, i32))
            new_rhs = builder.insert(arith.constant(2, i32))
            add = builder.insert(arith.addi(lhs.results[0], old_rhs.results[0]))
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            object.__setattr__(add, "operands", (lhs.results[0], new_rhs.results[0]))
            object.__setattr__(add, "operands", (lhs.results[0], old_rhs.results[0]))

        action = CompilerAction("bad-object-operands-assignment", assign_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertIs(add.operands[1], old_rhs.results[0])

    def test_action_apply_raw_object_properties_reassignment_cannot_silently_pass(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        original = const.properties
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            object.__setattr__(const, "properties", {"value": 8})
            object.__setattr__(const, "properties", original)

        action = CompilerAction("bad-object-properties-assignment", assign_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertIs(const.properties, original)
        self.assertEqual(const.properties["value"], 7)

    def test_action_apply_raw_object_attributes_reassignment_cannot_silently_pass(self) -> None:
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
            object.__setattr__(op, "attributes", {"tag": Attribute("tag", "after")})
            object.__setattr__(op, "attributes", original)

        action = CompilerAction("bad-object-attributes-assignment", assign_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertIs(op.attributes, original)
        self.assertEqual(op.attributes["tag"], Attribute("tag", "before"))

    def test_action_apply_raw_object_block_operations_reassignment_cannot_silently_pass(
        self,
    ) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            first = builder.insert(arith.constant(1, i32))
            second = builder.insert(arith.constant(2, i32))
        original = block._operations
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            object.__setattr__(block, "_operations", [second, first])
            object.__setattr__(block, "_operations", original)

        action = CompilerAction("bad-object-block-operations-assignment", assign_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertIs(block._operations, original)
        self.assertEqual(block.operations, (first, second))

    def test_action_apply_raw_object_region_blocks_reassignment_cannot_silently_pass(self) -> None:
        first_block = Block()
        second_block = Block()
        region = Region.from_block_list([first_block, second_block])
        module = builtin.module(region)
        original = region._blocks
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            object.__setattr__(region, "_blocks", [second_block, first_block])
            object.__setattr__(region, "_blocks", original)

        action = CompilerAction("bad-object-region-blocks-assignment", assign_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertIs(region._blocks, original)
        self.assertEqual(region.blocks, (first_block, second_block))

    def test_action_apply_raw_object_guarded_dict_data_reassignment_cannot_silently_pass(
        self,
    ) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        original = const.properties._data
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            object.__setattr__(const.properties, "_data", (("value", 8),))
            object.__setattr__(const.properties, "_data", original)

        action = CompilerAction("bad-object-guarded-dict-data-assignment", assign_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertEqual(const.properties["value"], 7)

    def test_action_apply_raw_object_guarded_list_data_reassignment_cannot_silently_pass(
        self,
    ) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            first = builder.insert(arith.constant(1, i32))
            second = builder.insert(arith.constant(2, i32))
        original = block._operations._data
        run = PipelineRun(module)

        def assign_then_restore(current_run):
            object.__setattr__(block._operations, "_data", (second, first))
            object.__setattr__(block._operations, "_data", original)

        action = CompilerAction("bad-object-guarded-list-data-assignment", assign_then_restore)

        with self.assertRaises((TypeError, AttributeError, ValueError)):
            action.run(run)

        self.assertEqual(block.operations, (first, second))


if __name__ == "__main__":
    unittest.main()
