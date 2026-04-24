import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class MutationGuardPublicTests(unittest.TestCase):
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

    def test_action_apply_block_argument_operand_mutation_restores_use_list(self) -> None:
        entry = Block()
        function_block = Block(arg_types=(i32,))
        function_region = Region.from_block_list([function_block])
        module = builtin.module(Region.from_block_list([entry]))
        with Builder().insert_at_end(function_block) as builder:
            replacement = builder.insert(arith.constant(9, i32))
            user = builder.insert(arith.addi(function_block.arguments[0], replacement.results[0]))
            builder.insert(func.return_(user.results[0]))
        function_type = func.FunctionType(inputs=(i32,), results=(i32,))
        with Builder().insert_at_end(entry) as builder:
            builder.insert(func.func("uses_arg", function_type, function_region))
        original_arg = function_block.arguments[0]
        run = PipelineRun(module)

        action = CompilerAction(
            "bad-block-argument-operand-mutation",
            lambda current_run: user.replace_operand(0, replacement.results[0]),
        )

        with self.assertRaisesRegex(ValueError, "direct syntax mutation"):
            action.run(run)

        self.assertIs(user.operands[0], original_arg)
        self.assertTrue(any(use.owner is user and use.operand_index == 0 for use in original_arg.uses))
        verify_operation(module)
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


if __name__ == "__main__":
    unittest.main()
