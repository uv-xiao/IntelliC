import unittest

from intellic.ir.dialects import arith, builtin
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import Block, Builder, Region, Type
from intellic.ir.syntax.printer import print_operation


def operation_names(op):
    names = [op.name]
    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                names.extend(operation_names(child))
    return names


class ParserPrinterTests(unittest.TestCase):
    def test_generic_roundtrip_preserves_nested_operation_structure(self) -> None:
        i32 = Type("i32")
        block = Block()
        region = Region.from_block_list([block])
        module = builtin.module(region)
        with Builder().insert_at_end(block) as builder:
            lhs = builder.insert(arith.constant(1, i32))
            rhs = builder.insert(arith.constant(2, i32))
            builder.insert(arith.addi(lhs.results[0], rhs.results[0]))

        text = print_operation(module)
        parsed = parse_operation(text)

        self.assertEqual(operation_names(parsed), operation_names(module))
        self.assertEqual(len(parsed.regions), 1)
        self.assertEqual(len(parsed.regions[0].blocks), 1)
        self.assertEqual(len(parsed.regions[0].blocks[0].operations), 3)

    def test_parser_rejects_unknown_custom_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected operation"):
            parse_operation("not-an-operation")

    def test_parser_rejects_unknown_value_use(self) -> None:
        text = '%0 = "arith.addi"(%missing, %missing) : () -> (i32)'

        with self.assertRaisesRegex(ValueError, "unknown SSA value"):
            parse_operation(text)


if __name__ == "__main__":
    unittest.main()
