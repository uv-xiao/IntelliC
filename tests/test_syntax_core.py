import unittest

from intellic.ir.syntax import (
    Block,
    Builder,
    Operation,
    Region,
    Type,
    VerificationError,
    verify_operation,
)


class SyntaxCoreTests(unittest.TestCase):
    def test_operation_create_owns_typed_results(self) -> None:
        i32 = Type("i32")

        op = Operation.create("arith.constant", result_types=(i32,))

        self.assertEqual(op.name, "arith.constant")
        self.assertIsNone(op.parent)
        self.assertEqual(len(op.results), 1)
        self.assertIs(op.results[0].owner, op)
        self.assertEqual(op.results[0].index, 0)
        self.assertEqual(op.results[0].type, i32)

    def test_builder_inserts_detached_operation_and_rejects_reparenting(self) -> None:
        block = Block()
        op = Operation.create("arith.constant", result_types=(Type("index"),))

        builder = Builder()
        with builder.insert_at_end(block):
            builder.insert(op)

        self.assertIs(op.parent, block)
        self.assertEqual(tuple(block.operations), (op,))

        with self.assertRaisesRegex(ValueError, "already has a parent"):
            with builder.insert_at_end(Block()):
                builder.insert(op)

    def test_operand_replacement_maintains_use_lists(self) -> None:
        i32 = Type("i32")
        lhs = Operation.create("arith.constant", result_types=(i32,))
        old_rhs = Operation.create("arith.constant", result_types=(i32,))
        new_rhs = Operation.create("arith.constant", result_types=(i32,))
        add = Operation.create(
            "arith.addi",
            operands=(lhs.results[0], old_rhs.results[0]),
            result_types=(i32,),
        )

        self.assertEqual(len(old_rhs.results[0].uses), 1)
        self.assertIs(old_rhs.results[0].uses[0].owner, add)
        self.assertEqual(old_rhs.results[0].uses[0].operand_index, 1)

        add.replace_operand(1, new_rhs.results[0])

        self.assertEqual(add.operands, (lhs.results[0], new_rhs.results[0]))
        self.assertEqual(old_rhs.results[0].uses, ())
        self.assertEqual(len(new_rhs.results[0].uses), 1)
        self.assertIs(new_rhs.results[0].uses[0].owner, add)

    def test_block_arguments_are_values_and_symbolic_values_reject_bool(self) -> None:
        i32 = Type("i32")
        block = Block(arg_types=(i32,))

        self.assertEqual(len(block.arguments), 1)
        self.assertIs(block.arguments[0].owner, block)
        self.assertEqual(block.arguments[0].index, 0)
        self.assertEqual(block.arguments[0].type, i32)

        with self.assertRaisesRegex(TypeError, "symbolic IR value"):
            bool(block.arguments[0])

    def test_verifier_accepts_consistent_region_and_rejects_broken_parent(self) -> None:
        i32 = Type("i32")
        block = Block()
        region = Region.from_block_list([block])
        const = Operation.create("arith.constant", result_types=(i32,))
        module = Operation.create("builtin.module", regions=(region,))

        with Builder().insert_at_end(block) as builder:
            builder.insert(const)

        verify_operation(module)

        const.parent = None

        with self.assertRaisesRegex(VerificationError, "parent"):
            verify_operation(module)


if __name__ == "__main__":
    unittest.main()
