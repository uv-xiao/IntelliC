import unittest

from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun, passes
from intellic.ir.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index


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
        evidence = run.db.require("RewriteEvidence", add.id).value
        self.assertEqual(evidence["action"], "canonicalize-greedy")
        self.assertEqual(evidence["replacement"], value.results[0].id)
        with self.assertRaisesRegex(ValueError, "pending records"):
            PendingRecordGate().run(run)

        MutatorStage().run(run)

        self.assertNotIn(add, block.operations)
        self.assertEqual(len(run.db.query("MutationApplied")), 1)
        PendingRecordGate().run(run)

    def test_verify_structure_records_diagnostic_and_evidence_link(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        run = PipelineRun(module)

        passes.verify_structure().run(run)

        diagnostic = run.db.require("Diagnostic", module.id).value
        evidence = run.db.require("EvidenceLink", module.id).value
        self.assertEqual(diagnostic["action"], "verify-structure")
        self.assertEqual(diagnostic["severity"], "info")
        self.assertEqual(evidence["action"], "verify-structure")
        self.assertEqual(evidence["subject"], module.id)

    def test_action_apply_direct_operand_mutation_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            lhs = builder.insert(arith.constant(7, i32))
            old_rhs = builder.insert(arith.constant(1, i32))
            new_rhs = builder.insert(arith.constant(2, i32))
            add = builder.insert(arith.addi(lhs.results[0], old_rhs.results[0]))
        run = PipelineRun(module)

        action = CompilerAction(
            "bad-direct-mutation",
            lambda current_run: add.replace_operand(1, new_rhs.results[0]),
        )

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-direct-mutation").value
        self.assertEqual(violation["before"], old_rhs.results[0].id)
        self.assertEqual(violation["after"], new_rhs.results[0].id)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

    def test_action_apply_direct_property_mutation_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        properties_ref = const.properties
        run = PipelineRun(module)

        action = CompilerAction(
            "bad-property-mutation",
            lambda current_run: const.properties.__setitem__("value", 8),
        )

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-property-mutation").value
        self.assertEqual(violation["kind"], "properties_changed")
        self.assertEqual(violation["before"]["value"], 7)
        self.assertEqual(violation["after"]["value"], 8)
        self.assertIs(const.properties, properties_ref)
        self.assertEqual(properties_ref["value"], 7)
        self.assertEqual(const.properties["value"], 7)
        with self.assertRaisesRegex(ValueError, "direct mutation violations"):
            PendingRecordGate().run(run)

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

    def test_action_apply_direct_property_mutation_then_exception_records_violation(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(7, i32))
        run = PipelineRun(module)

        def mutate_then_raise(current_run):
            const.properties["value"] = 8
            raise RuntimeError("boom")

        action = CompilerAction("bad-mutation-then-raise", mutate_then_raise)

        with self.assertRaises(RuntimeError):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-mutation-then-raise").value
        self.assertEqual(violation["kind"], "properties_changed")
        self.assertEqual(violation["before"]["value"], 7)
        self.assertEqual(violation["after"]["value"], 8)
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

    def test_action_apply_direct_attribute_mutation_is_rejected(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            op = builder.insert(
                Operation.create(
                    "test.with_attr",
                    attributes={"tag": Attribute("tag", "before")},
                )
            )
        run = PipelineRun(module)

        action = CompilerAction(
            "bad-attribute-mutation",
            lambda current_run: op.attributes.__setitem__("tag", Attribute("tag", "after")),
        )

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        violation = run.db.require("DirectMutationViolation", "bad-attribute-mutation").value
        self.assertEqual(violation["kind"], "attributes_changed")
        self.assertEqual(violation["before"]["tag"], Attribute("tag", "before"))
        self.assertEqual(violation["after"]["tag"], Attribute("tag", "after"))
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

    def test_dce_before_cse_rejects_replacement_to_erased_representative(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            representative = builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
            two = builder.insert(arith.constant(2, i32))
            user = builder.insert(arith.addi(duplicate.results[0], two.results[0]))
            builder.insert(Operation.create("test.consume", operands=(user.results[0],)))
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)
        passes.common_subexpression_elimination().run(run)

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", duplicate.id).value
        self.assertEqual(rejection.reason, "stale replacement value")
        self.assertNotIn(representative, block.operations)
        self.assertIn(duplicate, block.operations)
        self.assertIs(user.operands[0], duplicate.results[0])
        self.assertNoDetachedOperands(block)

    def test_constant_propagation_records_constant_facts(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(42, i32))
        run = PipelineRun(module)

        passes.sparse_constant_propagation().run(run)

        self.assertEqual(run.db.require("ValueConcrete", const.results[0].id).value, 42)
        value_range = run.db.require("ValueRange", const.results[0].id).value
        self.assertEqual(value_range["min"], 42)
        self.assertEqual(value_range["max"], 42)

    def test_constant_propagation_records_branch_and_region_reachability(self) -> None:
        block = Block()
        then_block = Block()
        else_block = Block()
        then_region = Region.from_block_list([then_block])
        else_region = Region.from_block_list([else_block])
        with Builder().insert_at_end(then_block) as builder:
            builder.insert(scf.yield_())
        with Builder().insert_at_end(else_block) as builder:
            builder.insert(scf.yield_())
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            condition = builder.insert(arith.constant(1, i1))
            if_op = builder.insert(
                scf.if_(condition.results[0], then_region=then_region, else_region=else_region)
            )
        run = PipelineRun(module)

        passes.sparse_constant_propagation().run(run)

        branch = run.db.require("BranchReachability", if_op.id).value
        then_reachability = run.db.require("RegionReachability", then_region.id).value
        else_reachability = run.db.require("RegionReachability", else_region.id).value
        self.assertTrue(branch["then_reachable"])
        self.assertFalse(branch["else_reachable"])
        self.assertTrue(then_reachability["reachable"])
        self.assertFalse(else_reachability["reachable"])

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

    def test_symbol_dce_records_liveness_and_erases_unused_pure_ops(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            dead = builder.insert(arith.constant(9, i32))
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)

        self.assertEqual(run.db.require("DeadCodeCandidate", dead.id).value["reason"], "unused pure op")
        self.assertEqual(run.db.require("MutationIntent", dead.id).value.kind, "erase_op")

        MutatorStage().run(run)

        self.assertNotIn(dead, block.operations)

    def test_symbol_dce_erases_unused_private_function(self) -> None:
        module_block = Block()
        module = builtin.module(Region.from_block_list([module_block]))
        function_type = func.FunctionType(inputs=(i32,), results=(i32,))
        function_block = Block(arg_types=(i32,))
        function_region = Region.from_block_list([function_block])
        with Builder().insert_at_end(function_block) as builder:
            builder.insert(func.return_(function_block.arguments[0]))
        dead_function = func.func("dead_private", function_type, function_region)
        dead_function.properties["sym_visibility"] = "private"
        with Builder().insert_at_end(module_block) as builder:
            builder.insert(dead_function)
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)

        self.assertFalse(run.db.require("SymbolLiveness", dead_function.id).value["live"])
        self.assertEqual(run.db.require("DeadCodeCandidate", dead_function.id).value["reason"], "unused function")
        self.assertEqual(run.db.require("MutationIntent", dead_function.id).value.kind, "erase_op")

        MutatorStage().run(run)

        self.assertNotIn(dead_function, module_block.operations)

    def test_symbol_dce_preserves_called_private_function(self) -> None:
        module_block = Block()
        module = builtin.module(Region.from_block_list([module_block]))
        function_type = func.FunctionType(inputs=(i32,), results=(i32,))

        callee_block = Block(arg_types=(i32,))
        callee_region = Region.from_block_list([callee_block])
        with Builder().insert_at_end(callee_block) as builder:
            builder.insert(func.return_(callee_block.arguments[0]))
        callee = func.func("called_private", function_type, callee_region)
        callee.properties["sym_visibility"] = "private"

        caller_block = Block(arg_types=(i32,))
        caller_region = Region.from_block_list([caller_block])
        with Builder().insert_at_end(caller_block) as builder:
            call = builder.insert(func.call("called_private", (caller_block.arguments[0],), function_type))
            builder.insert(func.return_(call.results[0]))
        caller = func.func("main", function_type, caller_region)

        with Builder().insert_at_end(module_block) as builder:
            builder.insert(callee)
            builder.insert(caller)
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)

        self.assertTrue(run.db.require("SymbolLiveness", callee.id).value["live"])
        with self.assertRaises(KeyError):
            run.db.require("MutationIntent", callee.id)

    def test_inline_single_call_records_callgraph_and_inline_intent(self) -> None:
        module_block = Block()
        module = builtin.module(Region.from_block_list([module_block]))
        callee_type = func.FunctionType(inputs=(i32,), results=(i32,))

        callee_block = Block(arg_types=(i32,))
        callee_region = Region.from_block_list([callee_block])
        with Builder().insert_at_end(callee_block) as builder:
            builder.insert(func.return_(callee_block.arguments[0]))
        callee = func.func("identity", callee_type, callee_region)

        caller_block = Block(arg_types=(i32,))
        caller_region = Region.from_block_list([caller_block])
        with Builder().insert_at_end(caller_block) as builder:
            call = builder.insert(func.call("identity", (caller_block.arguments[0],), callee_type))
            builder.insert(func.return_(call.results[0]))
        caller = func.func("caller", callee_type, caller_region)

        with Builder().insert_at_end(module_block) as builder:
            builder.insert(callee)
            builder.insert(caller)
        run = PipelineRun(module)

        passes.inline_single_call().run(run)

        self.assertEqual(run.db.require("CallGraphEdge", call.id).value["callee"], callee.id)
        inline = run.db.require("InlineIntent", call.id).value
        mapping = run.db.require("ClonedRegionMapping", call.id).value
        self.assertEqual(inline["callee"], callee.id)
        self.assertEqual(inline["strategy"], "single-return-forward")
        self.assertEqual(mapping["strategy"], "single-return-forward")
        self.assertEqual(mapping["call_results"], (call.results[0].id,))
        self.assertEqual(mapping["replacements"], (caller_block.arguments[0].id,))

    def test_inline_single_call_mutator_applies_block_argument_forwarding(self) -> None:
        module_block = Block()
        module = builtin.module(Region.from_block_list([module_block]))
        callee_type = func.FunctionType(inputs=(i32,), results=(i32,))

        callee_block = Block(arg_types=(i32,))
        callee_region = Region.from_block_list([callee_block])
        with Builder().insert_at_end(callee_block) as builder:
            builder.insert(func.return_(callee_block.arguments[0]))
        callee = func.func("identity", callee_type, callee_region)

        caller_block = Block(arg_types=(i32,))
        caller_region = Region.from_block_list([caller_block])
        with Builder().insert_at_end(caller_block) as builder:
            call = builder.insert(func.call("identity", (caller_block.arguments[0],), callee_type))
            ret = builder.insert(func.return_(call.results[0]))
        caller = func.func("caller", callee_type, caller_region)

        with Builder().insert_at_end(module_block) as builder:
            builder.insert(callee)
            builder.insert(caller)
        run = PipelineRun(module)

        passes.inline_single_call().run(run)
        MutatorStage().run(run)

        self.assertNotIn(call, caller_block.operations)
        self.assertIs(ret.operands[0], caller_block.arguments[0])
        self.assertEqual(run.db.query("MutationRejected", call.id), ())
        PendingRecordGate().run(run)

    def test_loop_invariant_code_motion_records_loop_scope_and_candidate(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            lower = builder.insert(arith.constant(0, index)).results[0]
            upper = builder.insert(arith.constant(8, index)).results[0]
            step = builder.insert(arith.constant(1, index)).results[0]

        body_block = Block(arg_types=(index,))
        body = Region.from_block_list([body_block])
        with Builder().insert_at_end(body_block) as builder:
            invariant = builder.insert(arith.constant(4, i32))
            builder.insert(scf.yield_())

        with Builder().insert_at_end(block) as builder:
            loop = builder.insert(scf.for_(lower, upper, step, body=body))
        run = PipelineRun(module)

        passes.loop_invariant_code_motion().run(run)

        self.assertEqual(run.db.require("LoopScope", loop.id).value["kind"], "scf.for")
        move = run.db.require("LoopInvariantCandidate", invariant.id).value
        side_effect = run.db.require("SideEffectFact", invariant.id).value
        moved = run.db.require("MovedOpEvidence", invariant.id).value
        self.assertEqual(move["loop"], loop.id)
        self.assertEqual(move["action"], "would_move_before_loop")
        self.assertEqual(side_effect["effect"], "none")
        self.assertEqual(moved["target"], "before-loop")
        self.assertEqual(moved["status"], "record-only")

    def test_lower_affine_to_scf_records_dim_symbol_mapping_for_affine_apply(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            dim = builder.insert(arith.constant(3, index)).results[0]
            symbol = builder.insert(arith.constant(5, index)).results[0]
            affine_apply = builder.insert(
                affine.apply(affine.AffineMap(1, 1, ("d0 + s0",)), (dim,), (symbol,))
            )
        run = PipelineRun(module)

        passes.lower_affine_to_scf().run(run)

        mapping = run.db.require("AffineDimSymbolMapping", affine_apply.id).value
        expansion = run.db.require("AffineExpansion", affine_apply.id).value
        self.assertEqual(mapping["dims"], (dim.id,))
        self.assertEqual(mapping["symbols"], (symbol.id,))
        self.assertEqual(expansion["results"], ("d0 + s0",))

    def test_normalize_affine_loops_records_normalized_bounds(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        lower = affine.AffineMap(0, 0, ("0",))
        upper = affine.AffineMap(0, 0, ("16",))
        loop_body = Region.from_block_list([Block()])
        with Builder().insert_at_end(block) as builder:
            loop = builder.insert(affine.for_(lower, upper, 4, (), loop_body))
        run = PipelineRun(module)

        passes.normalize_and_simplify_affine_loops().run(run)

        bounds = run.db.require("AffineLoopBounds", loop.id).value
        band = run.db.require("AffineLoopBand", loop.id).value
        normalized = run.db.require("AffineNormalizedBounds", loop.id).value
        self.assertEqual(bounds["step"], 4)
        self.assertEqual(band["loops"], (loop.id,))
        self.assertEqual(normalized["lower"], ("0",))
        self.assertEqual(normalized["upper"], ("16",))

    def test_pending_record_gate_records_success_after_mutations_are_consumed(self) -> None:
        module = builtin.module(Region.from_block_list([Block()]))
        run = PipelineRun(module)

        PendingRecordGate().run(run)

        self.assertEqual(run.db.require("PendingRecordGate", module.id).value["status"], "passed")

    def test_mutator_rejects_stale_mutation_intent_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            stale = builder.insert(arith.constant(11, i32))
        run = PipelineRun(module)
        run.db.put("MutationIntent", stale.id, MutationIntent("erase_op", stale, reason="stale test"))
        block._operations.remove(stale)

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", stale.id).value
        self.assertEqual(rejection.intent.subject, stale)
        self.assertEqual(rejection.reason, "stale mutation subject")
        self.assertEqual(run.db.query("MutationIntent", stale.id), ())
        PendingRecordGate().run(run)

    def test_mutator_rejects_erasing_used_result_producer_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            used = builder.insert(arith.constant(13, i32))
            zero = builder.insert(arith.constant(0, i32))
            user = builder.insert(arith.addi(used.results[0], zero.results[0]))
        run = PipelineRun(module)
        run.db.put("MutationIntent", used.id, MutationIntent("erase_op", used, reason="unsafe test"))

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", used.id).value
        self.assertEqual(rejection.reason, "used result producer")
        self.assertIn(used, block.operations)
        self.assertIs(user.operands[0], used.results[0])
        self.assertEqual(run.db.query("MutationIntent", used.id), ())
        PendingRecordGate().run(run)

    def test_mutator_rejects_self_replacement_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            subject = builder.insert(arith.constant(21, i32))
            zero = builder.insert(arith.constant(0, i32))
            user = builder.insert(arith.addi(subject.results[0], zero.results[0]))
        run = PipelineRun(module)
        run.db.put(
            "MutationIntent",
            subject.id,
            MutationIntent(
                "replace_uses_and_erase",
                subject,
                subject.results[0],
                reason="self replacement test",
            ),
        )

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", subject.id).value
        self.assertEqual(rejection.reason, "self replacement value")
        self.assertIn(subject, block.operations)
        self.assertIs(user.operands[0], subject.results[0])
        self.assertNoDetachedOperands(block)
        PendingRecordGate().run(run)

    def test_mutator_rejects_later_same_block_replacement_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            old = builder.insert(arith.constant(1, i32))
            zero = builder.insert(arith.constant(0, i32))
            user = builder.insert(arith.addi(old.results[0], zero.results[0]))
            later = builder.insert(arith.constant(2, i32))
        run = PipelineRun(module)
        run.db.put(
            "MutationIntent",
            old.id,
            MutationIntent(
                "replace_uses_and_erase",
                old,
                later.results[0],
                reason="later replacement test",
            ),
        )

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", old.id).value
        self.assertEqual(rejection.reason, "replacement does not dominate use")
        self.assertIn(old, block.operations)
        self.assertIs(user.operands[0], old.results[0])
        self.assertNoDetachedOperands(block)
        PendingRecordGate().run(run)

    def assertNoDetachedOperands(self, block: Block) -> None:
        operations = set(block.operations)
        for op in block.operations:
            for operand in op.operands:
                owner = getattr(operand, "owner", None)
                if isinstance(owner, Operation):
                    self.assertIn(owner, operations)


if __name__ == "__main__":
    unittest.main()
