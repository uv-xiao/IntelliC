import unittest

from intellic.ir.dialects import arith, builtin, scf
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import Block, Builder, Region, Type, i1, i32
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

    def test_generic_roundtrip_preserves_scf_if_regions(self) -> None:
        module_region = Region.from_block_list([Block()])
        then_region = Region.from_block_list([Block()])
        else_region = Region.from_block_list([Block()])
        module = builtin.module(module_region)
        with Builder().insert_at_end(module_region.blocks[0]) as builder:
            condition = builder.insert(arith.constant(1, i1)).results[0]
            then_value = builder.insert(arith.constant(10, i32)).results[0]
            else_value = builder.insert(arith.constant(20, i32)).results[0]
            with Builder().insert_at_end(then_region.blocks[0]) as then_builder:
                then_builder.insert(scf.yield_(then_value))
            with Builder().insert_at_end(else_region.blocks[0]) as else_builder:
                else_builder.insert(scf.yield_(else_value))
            builder.insert(
                scf.if_(
                    condition,
                    result_types=(i32,),
                    then_region=then_region,
                    else_region=else_region,
                )
            )

        text = print_operation(module)
        parsed = parse_operation(text)
        parsed_if = parsed.regions[0].blocks[0].operations[-1]

        self.assertEqual(parsed_if.name, "scf.if")
        self.assertEqual(len(parsed_if.regions), 2)
        self.assertEqual(
            [block.operations[0].name for region in parsed_if.regions for block in region.blocks],
            ["scf.yield", "scf.yield"],
        )


if __name__ == "__main__":
    unittest.main()
