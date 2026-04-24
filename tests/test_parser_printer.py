import unittest

from intellic.ir.dialects import affine, arith, builtin, scf
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import (
    Attribute,
    Block,
    Builder,
    Operation,
    Region,
    Type,
    VerificationError,
    i1,
    i32,
    verify_operation,
)
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

    def test_parser_rejects_parent_use_of_region_local_value(self) -> None:
        text = """
        "test.parent"(%0) ({
          %0 = "arith.constant"() {'value': 1} : () -> (i32)
        }) : () -> ()
        """

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

    def test_generic_roundtrip_preserves_execute_region_blocks(self) -> None:
        region = Region.from_block_list([Block(), Block()])
        for index, block in enumerate(region.blocks):
            with Builder().insert_at_end(block) as builder:
                builder.insert(arith.constant(index, i32))
                builder.insert(scf.yield_())
        op = scf.execute_region(region, no_inline=True)

        text = print_operation(op)
        parsed = parse_operation(text)

        self.assertEqual(parsed.name, "scf.execute_region")
        self.assertEqual(len(parsed.regions), 1)
        self.assertEqual(len(parsed.regions[0].blocks), 2)
        self.assertEqual(
            [block.operations[0].name for block in parsed.regions[0].blocks],
            ["arith.constant", "arith.constant"],
        )

    def test_generic_roundtrip_preserves_scf_contract_properties(self) -> None:
        module_region = Region.from_block_list([Block()])
        module = builtin.module(module_region)

        execute_region = Region.from_block_list([Block()])
        with Builder().insert_at_end(execute_region.blocks[0]) as builder:
            builder.insert(arith.constant(42, i32))
            builder.insert(scf.yield_())

        switch_region = Region.from_block_list([Block()])
        default_region = Region.from_block_list([Block()])
        forall_yield_region = Region.from_block_list([Block(arg_types=(i32,))])
        with Builder().insert_at_end(forall_yield_region.blocks[0]) as builder:
            builder.insert(scf.yield_(forall_yield_region.blocks[0].arguments[0]))
        forall_body = Region.from_block_list([Block(arg_types=(Type("index"), i32))])
        with Builder().insert_at_end(module_region.blocks[0]) as module_builder:
            flag = module_builder.insert(arith.constant(0, Type("index"))).results[0]
            lower = module_builder.insert(arith.constant(0, Type("index"))).results[0]
            upper = module_builder.insert(arith.constant(4, Type("index"))).results[0]
            step = module_builder.insert(arith.constant(1, Type("index"))).results[0]
            result = module_builder.insert(arith.constant(9, i32)).results[0]
            with Builder().insert_at_end(switch_region.blocks[0]) as builder:
                builder.insert(scf.yield_(result))
            with Builder().insert_at_end(default_region.blocks[0]) as builder:
                builder.insert(scf.yield_(result))
            with Builder().insert_at_end(forall_body.blocks[0]) as builder:
                builder.insert(
                    scf.forall_in_parallel(
                        scf.forall_yield(
                            forall_body.blocks[0].arguments[1],
                            region=forall_yield_region,
                        )
                    )
                )
            module_builder.insert(scf.execute_region(execute_region, no_inline=True))
            module_builder.insert(
                scf.index_switch(
                    flag,
                    (3,),
                    (switch_region,),
                    default_region,
                    result_types=(i32,),
                )
            )
            module_builder.insert(
                scf.forall(
                    lower_bounds=(lower,),
                    upper_bounds=(upper,),
                    steps=(step,),
                    shared_outputs=(result,),
                    body=forall_body,
                    mapping=("thread-x",),
                )
            )

        parsed = parse_operation(print_operation(module))
        parsed_execute, parsed_switch, parsed_forall = parsed.regions[0].blocks[0].operations[-3:]

        self.assertEqual(parsed_execute.properties["no_inline"], True)
        self.assertEqual(parsed_switch.properties["case_values"], (3,))
        self.assertEqual(parsed_forall.properties["mapping"], ("thread-x",))

    def test_generic_roundtrip_preserves_attribute_mapping_property(self) -> None:
        module_region = Region.from_block_list([Block()])
        module = builtin.module(module_region)
        yield_region = Region.from_block_list([Block(arg_types=(i32,))])
        with Builder().insert_at_end(yield_region.blocks[0]) as builder:
            builder.insert(scf.yield_(yield_region.blocks[0].arguments[0]))
        body = Region.from_block_list([Block(arg_types=(Type("index"), i32))])
        mapping = (Attribute("gpu.thread", "x"),)
        with Builder().insert_at_end(module_region.blocks[0]) as module_builder:
            lower = module_builder.insert(arith.constant(0, Type("index"))).results[0]
            upper = module_builder.insert(arith.constant(4, Type("index"))).results[0]
            step = module_builder.insert(arith.constant(1, Type("index"))).results[0]
            shared = module_builder.insert(arith.constant(0, i32)).results[0]
            with Builder().insert_at_end(body.blocks[0]) as builder:
                builder.insert(
                    scf.forall_in_parallel(
                        scf.forall_yield(body.blocks[0].arguments[1], region=yield_region)
                    )
                )
            module_builder.insert(
                scf.forall(
                    lower_bounds=(lower,),
                    upper_bounds=(upper,),
                    steps=(step,),
                    shared_outputs=(shared,),
                    body=body,
                    mapping=mapping,
                )
            )

        parsed = parse_operation(print_operation(module))
        parsed_forall = parsed.regions[0].blocks[0].operations[-1]

        self.assertEqual(parsed_forall.properties["mapping"], mapping)

    def test_generic_roundtrip_preserves_affine_map_property(self) -> None:
        module_region = Region.from_block_list([Block()])
        module = builtin.module(module_region)
        map_ = affine.AffineMap(dim_count=1, symbol_count=0, results=("d0",))
        with Builder().insert_at_end(module_region.blocks[0]) as builder:
            dim = builder.insert(arith.constant(0, Type("index"))).results[0]
            builder.insert(affine.min(map_, dims=(dim,), symbols=()))

        parsed = parse_operation(print_operation(module))
        parsed_min = parsed.regions[0].blocks[0].operations[-1]

        self.assertEqual(parsed_min.properties["map"], map_)

    def test_printer_rejects_unsupported_property_values(self) -> None:
        op = Operation.create("test.unsupported", properties={"payload": object()})

        with self.assertRaisesRegex(TypeError, "unsupported property"):
            print_operation(op)

    def test_verify_rejects_malformed_parsed_scf_if(self) -> None:
        text = """
        "builtin.module"() ({
          %0 = "arith.constant"() {'value': 0} : () -> (index)
          "scf.if"(%0) ({
            "scf.condition"(%0) : () -> ()
          }) : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.if"):
            verify_operation(parsed)

    def test_verify_rejects_scf_condition_outside_while_before_region(self) -> None:
        text = """
        "builtin.module"() ({
          %0 = "arith.constant"() {'value': 1} : () -> (i1)
          "scf.condition"(%0) : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.condition"):
            verify_operation(parsed)

    def test_verify_rejects_scf_reduce_return_outside_reduce_region(self) -> None:
        text = """
        "builtin.module"() ({
          %0 = "arith.constant"() {'value': 1} : () -> (i32)
          "scf.reduce.return"(%0) : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.reduce.return"):
            verify_operation(parsed)

    def test_verify_rejects_non_terminal_scf_yield(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.yield"() : () -> ()
          %0 = "arith.constant"() {'value': 1} : () -> (i32)
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.yield"):
            verify_operation(parsed)

    def test_verify_rejects_standalone_scf_forall_in_parallel(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.forall.in_parallel"() {'yield_count': 0} : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.forall.in_parallel"):
            verify_operation(parsed)

    def test_verify_rejects_standalone_scf_reduce(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.reduce"() {'operand_count': 0} : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.reduce"):
            verify_operation(parsed)

    def test_verify_rejects_non_terminal_scf_reduce(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.reduce"() {'operand_count': 0} : () -> ()
          %0 = "arith.constant"() {'value': 1} : () -> (i32)
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.reduce"):
            verify_operation(parsed)


if __name__ == "__main__":
    unittest.main()
