import unittest

from intellic.dialects import affine, arith, builtin, func, memref, scf, vector
from intellic.ir.syntax import Block, Builder, Operation, Region, VerificationError, i1, i32, index, verify_operation


class ScfControlTests(unittest.TestCase):
    def _single_block_region(self, arg_types=(), terminator_factory=None) -> Region:
        region = Region.from_block_list([Block(arg_types=arg_types)])
        if terminator_factory is not None:
            with scf.body_builder(region) as builder:
                builder.insert(terminator_factory(region.blocks[0].arguments))
        return region

    def test_scf_for_verifies_loop_carried_yield(self) -> None:
        lower = arith.constant(0, index).results[0]
        upper = arith.constant(4, index).results[0]
        step = arith.constant(1, index).results[0]
        initial = arith.constant(0, i32).results[0]
        body = Region.from_block_list([Block(arg_types=(index, i32))])
        with scf.body_builder(body) as builder:
            builder.insert(scf.yield_(initial))

        loop = scf.for_(lower, upper, step, iter_args=(initial,), body=body)

        self.assertEqual(loop.name, "scf.for")
        self.assertEqual(loop.results[0].type, i32)

        bad_body = Region.from_block_list([Block(arg_types=(index, i32))])
        with scf.body_builder(bad_body) as builder:
            builder.insert(scf.yield_())
        with self.assertRaisesRegex(ValueError, "yield count"):
            scf.for_(lower, upper, step, iter_args=(initial,), body=bad_body)

    def test_scf_if_verifies_condition_regions_and_branch_yields(self) -> None:
        condition = arith.constant(1, i1).results[0]
        value = arith.constant(7, i32).results[0]
        then_region = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_(value)
        )
        else_region = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_(value)
        )

        if_op = scf.if_(
            condition,
            result_types=(i32,),
            then_region=then_region,
            else_region=else_region,
        )

        self.assertEqual(if_op.name, "scf.if")
        self.assertEqual(if_op.results[0].type, i32)

        with self.assertRaisesRegex(TypeError, "condition"):
            scf.if_(arith.constant(0, index).results[0], then_region=self._single_block_region())

        bad_then = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_(arith.constant(0, index).results[0])
        )
        bad_else = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_(value)
        )
        with self.assertRaisesRegex(TypeError, "yield type"):
            scf.if_(condition, result_types=(i32,), then_region=bad_then, else_region=bad_else)

    def test_scf_if_rejects_zero_result_wrong_terminator(self) -> None:
        condition = arith.constant(1, i1).results[0]
        bad_then = self._single_block_region(
            terminator_factory=lambda _args: scf.condition(condition)
        )

        with self.assertRaisesRegex(ValueError, "scf.yield"):
            scf.if_(condition, then_region=bad_then)

    def test_scf_if_accepts_zero_result_regions_without_explicit_yield(self) -> None:
        condition = arith.constant(1, i1).results[0]
        then_region = Region.from_block_list([Block()])
        else_region = Region.from_block_list([Block()])

        op = scf.if_(condition, then_region=then_region, else_region=else_region)

        self.assertEqual(op.name, "scf.if")
        verify_operation(op)

    def test_scf_while_verifies_condition_payload_and_after_yield(self) -> None:
        initial = arith.constant(0, i32).results[0]
        condition = arith.constant(1, i1).results[0]
        before_region = self._single_block_region(
            arg_types=(i32,),
            terminator_factory=lambda args: scf.condition(condition, args[0]),
        )
        after_region = self._single_block_region(
            arg_types=(i32,),
            terminator_factory=lambda args: scf.yield_(args[0]),
        )

        while_op = scf.while_((initial,), before_region=before_region, after_region=after_region)

        self.assertEqual(while_op.name, "scf.while")
        self.assertEqual(while_op.results[0].type, i32)

        bad_before = self._single_block_region(
            arg_types=(i32,),
            terminator_factory=lambda _args: scf.condition(condition),
        )
        with self.assertRaisesRegex(ValueError, "condition payload"):
            scf.while_((initial,), before_region=bad_before, after_region=after_region)

    def test_scf_while_allows_payload_result_types_to_differ_from_next_operands(self) -> None:
        initial = arith.constant(0, i32).results[0]
        next_initial = arith.constant(1, i32).results[0]
        condition = arith.constant(1, i1).results[0]
        payload = arith.constant(0, index).results[0]
        before_region = self._single_block_region(
            arg_types=(i32,),
            terminator_factory=lambda _args: scf.condition(condition, payload),
        )
        after_region = self._single_block_region(
            arg_types=(index,),
            terminator_factory=lambda _args: scf.yield_(next_initial),
        )

        while_op = scf.while_(
            (initial,),
            before_region=before_region,
            after_region=after_region,
            result_types=(index,),
        )

        self.assertEqual(while_op.results[0].type, index)

        bad_after_region = self._single_block_region(
            arg_types=(index,),
            terminator_factory=lambda args: scf.yield_(args[0]),
        )
        with self.assertRaisesRegex(TypeError, "after region yield type"):
            scf.while_(
                (initial,),
                before_region=before_region,
                after_region=bad_after_region,
                result_types=(index,),
            )

    def test_scf_execute_region_allows_multiblock_and_verifies_yields(self) -> None:
        value = arith.constant(7, i32).results[0]
        first = Block()
        second = Block()
        region = Region.from_block_list([first, second])
        for block in region.blocks:
            builder = Builder()
            with builder.insert_at_end(block):
                builder.insert(scf.yield_(value))

        op = scf.execute_region(region, result_types=(i32,), no_inline=True)

        self.assertEqual(op.name, "scf.execute_region")
        self.assertTrue(op.properties["no_inline"])

        bad_region = Region.from_block_list([Block()])
        with self.assertRaisesRegex(ValueError, "terminate with scf.yield"):
            scf.execute_region(bad_region, result_types=(i32,))

    def test_scf_execute_region_rejects_zero_result_wrong_terminator(self) -> None:
        condition = arith.constant(1, i1).results[0]
        bad_region = self._single_block_region(
            terminator_factory=lambda _args: scf.condition(condition)
        )

        with self.assertRaisesRegex(ValueError, "scf.yield"):
            scf.execute_region(bad_region)

    def test_scf_index_switch_verifies_index_cases_and_region_yields(self) -> None:
        flag = arith.constant(0, index).results[0]
        value = arith.constant(7, i32).results[0]
        case_regions = (
            self._single_block_region(terminator_factory=lambda _args: scf.yield_(value)),
            self._single_block_region(terminator_factory=lambda _args: scf.yield_(value)),
        )
        default_region = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_(value)
        )

        op = scf.index_switch(flag, (0, 1), case_regions, default_region, result_types=(i32,))

        self.assertEqual(op.name, "scf.index_switch")
        self.assertEqual(op.results[0].type, i32)

        with self.assertRaisesRegex(TypeError, "index flag"):
            scf.index_switch(
                arith.constant(0, i32).results[0],
                (),
                (),
                self._single_block_region(),
            )

        with self.assertRaisesRegex(ValueError, "case values"):
            scf.index_switch(
                flag,
                (0, 0),
                (
                    self._single_block_region(terminator_factory=lambda _args: scf.yield_(value)),
                    self._single_block_region(terminator_factory=lambda _args: scf.yield_(value)),
                ),
                self._single_block_region(terminator_factory=lambda _args: scf.yield_(value)),
                result_types=(i32,),
            )

    def test_scf_index_switch_rejects_zero_result_wrong_terminator(self) -> None:
        flag = arith.constant(0, index).results[0]
        condition = arith.constant(1, i1).results[0]
        bad_case = self._single_block_region(
            terminator_factory=lambda _args: scf.condition(condition)
        )
        default_region = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_()
        )

        with self.assertRaisesRegex(ValueError, "scf.yield"):
            scf.index_switch(flag, (0,), (bad_case,), default_region)

    def test_verify_rejects_index_switch_non_integer_case_values(self) -> None:
        flag = arith.constant(0, index).results[0]
        case_region = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_()
        )
        default_region = self._single_block_region(
            terminator_factory=lambda _args: scf.yield_()
        )
        op = Operation.create(
            "scf.index_switch",
            operands=(flag,),
            properties={"case_values": ("zero",)},
            regions=(case_region, default_region),
        )

        with self.assertRaisesRegex(VerificationError, "case values"):
            verify_operation(op)


if __name__ == "__main__":
    unittest.main()
