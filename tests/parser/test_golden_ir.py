import unittest

from intellic.dialects import arith, builtin
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import Block, Builder, Region, Type
from intellic.ir.syntax.printer import print_operation


class GoldenIRTests(unittest.TestCase):
    def test_small_module_prints_golden_ir_and_parse_print_is_idempotent(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            lhs = builder.insert(arith.constant(1, Type("i32")))
            rhs = builder.insert(arith.constant(2, Type("i32")))
            builder.insert(arith.addi(lhs.results[0], rhs.results[0]))

        original = print_operation(module)
        golden = "\n".join(
            (
                '"builtin.module"() ({',
                '  %0 = "arith.constant"() <{value = 1}> : () -> i32',
                '  %1 = "arith.constant"() <{value = 2}> : () -> i32',
                '  %2 = "arith.addi"(%0, %1) : (i32, i32) -> i32',
                "}) : () -> ()",
            )
        )

        self.assertEqual(original, golden)
        self.assertNotIn("{'value':", original)
        self.assertEqual(original, print_operation(parse_operation(original)))


if __name__ == "__main__":
    unittest.main()
