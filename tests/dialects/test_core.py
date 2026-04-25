import unittest

from intellic.dialects import affine, arith, builtin, func, memref, scf, vector
from intellic.ir.syntax import Block, Builder, Operation, Region, VerificationError, i1, i32, index, verify_operation


class CoreTests(unittest.TestCase):
    def test_builtin_module_owns_region(self) -> None:
        region = Region.from_block_list([Block()])

        module = builtin.module(region)

        self.assertEqual(module.name, "builtin.module")
        self.assertIs(module.regions[0], region)
        self.assertIs(region.parent, module)

    def test_func_call_verifies_symbol_signature(self) -> None:
        function_type = func.FunctionType(inputs=(i32,), results=(i32,))
        arg = Operation.create("test.arg", result_types=(i32,)).results[0]

        call = func.call("callee", (arg,), function_type)

        self.assertEqual(call.name, "func.call")
        self.assertEqual(call.results[0].type, i32)

        with self.assertRaisesRegex(ValueError, "operand count"):
            func.call("callee", (), function_type)

        with self.assertRaisesRegex(TypeError, "operand 0"):
            func.call("callee", (Operation.create("test.arg", result_types=(index,)).results[0],), function_type)

    def test_arith_builders_verify_operand_types(self) -> None:
        lhs = arith.constant(1, i32)
        rhs = arith.constant(2, i32)

        add = arith.addi(lhs.results[0], rhs.results[0])
        cast = arith.index_cast(arith.constant(1, index).results[0], i32)

        self.assertEqual(add.results[0].type, i32)
        self.assertEqual(cast.results[0].type, i32)

        with self.assertRaisesRegex(TypeError, "same type"):
            arith.addi(lhs.results[0], arith.constant(1, index).results[0])


if __name__ == "__main__":
    unittest.main()
