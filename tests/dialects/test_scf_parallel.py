import unittest

from intellic.dialects import affine, arith, builtin, func, memref, scf, vector
from intellic.ir.syntax import Block, Builder, Operation, Region, VerificationError, i1, i32, index, verify_operation


class ScfParallelTests(unittest.TestCase):
    def _single_block_region(self, arg_types=(), terminator_factory=None) -> Region:
        region = Region.from_block_list([Block(arg_types=arg_types)])
        if terminator_factory is not None:
            with scf.body_builder(region) as builder:
                builder.insert(terminator_factory(region.blocks[0].arguments))
        return region

    def test_scf_parallel_reduce_and_reduce_return_verify_rank_and_types(self) -> None:
        lower = arith.constant(0, index).results[0]
        upper = arith.constant(4, index).results[0]
        step = arith.constant(1, index).results[0]
        initial = arith.constant(0, i32).results[0]
        reduce_region = self._single_block_region(
            arg_types=(i32, i32),
            terminator_factory=lambda args: scf.reduce_return(args[0]),
        )
        body = self._single_block_region(
            arg_types=(index, index),
            terminator_factory=lambda _args: scf.reduce(initial, regions=(reduce_region,)),
        )

        op = scf.parallel(
            lower_bounds=(lower, lower),
            upper_bounds=(upper, upper),
            steps=(step, step),
            init_vals=(initial,),
            body=body,
        )

        self.assertEqual(op.name, "scf.parallel")
        self.assertEqual(op.results[0].type, i32)

        with self.assertRaisesRegex(ValueError, "equal rank"):
            scf.parallel(
                lower_bounds=(lower,),
                upper_bounds=(upper, upper),
                steps=(step,),
                body=body,
            )

        bad_reduce_region = self._single_block_region(
            arg_types=(i32, i32),
            terminator_factory=lambda _args: scf.reduce_return(lower),
        )
        with self.assertRaisesRegex(TypeError, "reduce.return"):
            scf.reduce(initial, regions=(bad_reduce_region,))

        bad_body = self._single_block_region(
            arg_types=(index, index),
            terminator_factory=lambda _args: Operation.create(
                "scf.reduce",
                operands=(initial,),
                regions=(),
            ),
        )
        with self.assertRaisesRegex(ValueError, "reduction region"):
            scf.parallel(
                lower_bounds=(lower, lower),
                upper_bounds=(upper, upper),
                steps=(step, step),
                init_vals=(initial,),
                body=bad_body,
            )

        no_result_reduce_body = self._single_block_region(
            arg_types=(index, index),
            terminator_factory=lambda _args: Operation.create(
                "scf.reduce",
                operands=(initial,),
                regions=(),
            ),
        )
        with self.assertRaisesRegex(ValueError, "no-result"):
            scf.parallel(
                lower_bounds=(lower, lower),
                upper_bounds=(upper, upper),
                steps=(step, step),
                body=no_result_reduce_body,
            )

        unterminated_body = Region.from_block_list([Block(arg_types=(index, index))])
        with self.assertRaisesRegex(ValueError, "scf.reduce"):
            scf.parallel(
                lower_bounds=(lower, lower),
                upper_bounds=(upper, upper),
                steps=(step, step),
                body=unterminated_body,
            )

        wrong_terminator_body = self._single_block_region(
            arg_types=(index, index),
            terminator_factory=lambda _args: Operation.create("test.terminator"),
        )
        with self.assertRaisesRegex(ValueError, "scf.reduce"):
            scf.parallel(
                lower_bounds=(lower, lower),
                upper_bounds=(upper, upper),
                steps=(step, step),
                body=wrong_terminator_body,
            )

        yield_body = self._single_block_region(
            arg_types=(index, index),
            terminator_factory=lambda _args: scf.yield_(),
        )
        with self.assertRaisesRegex(ValueError, "scf.reduce"):
            scf.parallel(
                lower_bounds=(lower, lower),
                upper_bounds=(upper, upper),
                steps=(step, step),
                body=yield_body,
            )

    def test_verify_rejects_parallel_result_init_type_mismatch(self) -> None:
        lower = arith.constant(0, index).results[0]
        upper = arith.constant(4, index).results[0]
        step = arith.constant(1, index).results[0]
        initial = arith.constant(0, i32).results[0]
        reduce_region = self._single_block_region(
            arg_types=(index, index),
            terminator_factory=lambda args: scf.reduce_return(args[0]),
        )
        body = self._single_block_region(
            arg_types=(index,),
            terminator_factory=lambda _args: scf.reduce(lower, regions=(reduce_region,)),
        )
        op = Operation.create(
            "scf.parallel",
            operands=(lower, upper, step, initial),
            result_types=(index,),
            properties={"rank": 1, "init_count": 1},
            regions=(body,),
        )

        with self.assertRaisesRegex(VerificationError, "result types"):
            verify_operation(op)

    def test_scf_forall_verifies_parallel_terminator_and_shared_outputs(self) -> None:
        lower = arith.constant(0, index).results[0]
        upper = arith.constant(4, index).results[0]
        step = arith.constant(1, index).results[0]
        shared = arith.constant(0, i32).results[0]
        yield_region = self._single_block_region(
            arg_types=(i32,),
            terminator_factory=lambda args: scf.yield_(args[0]),
        )
        body = self._single_block_region(
            arg_types=(index, index, i32),
            terminator_factory=lambda args: scf.forall_in_parallel(
                scf.forall_yield(args[2], region=yield_region)
            ),
        )

        op = scf.forall(
            lower_bounds=(lower, lower),
            upper_bounds=(upper, upper),
            steps=(step, step),
            shared_outputs=(shared,),
            body=body,
            mapping=("thread-x", "thread-y"),
        )

        self.assertEqual(op.name, "scf.forall")
        self.assertEqual(op.results[0].type, i32)
        self.assertEqual(op.properties["mapping"], ("thread-x", "thread-y"))
        self.assertEqual(body.blocks[0].operations[-1].regions, (yield_region,))

        bad_body = self._single_block_region(
            arg_types=(index, index, i32),
            terminator_factory=lambda args: scf.yield_(args[2]),
        )
        with self.assertRaisesRegex(ValueError, "forall.in_parallel"):
            scf.forall(
                lower_bounds=(lower, lower),
                upper_bounds=(upper, upper),
                steps=(step, step),
                shared_outputs=(shared,),
                body=bad_body,
            )

        bad_output_body = self._single_block_region(
            arg_types=(index, index, i32),
            terminator_factory=lambda _args: scf.forall_in_parallel(
                scf.forall_yield(lower, region=self._single_block_region(
                    arg_types=(index,),
                    terminator_factory=lambda args: scf.yield_(args[0]),
                ))
            ),
        )
        with self.assertRaisesRegex(TypeError, "shared output"):
            scf.forall(
                lower_bounds=(lower, lower),
                upper_bounds=(upper, upper),
                steps=(step, step),
                shared_outputs=(shared,),
                body=bad_output_body,
            )

    def test_verify_rejects_forall_result_shared_output_type_mismatch(self) -> None:
        lower = arith.constant(0, index).results[0]
        upper = arith.constant(4, index).results[0]
        step = arith.constant(1, index).results[0]
        shared = arith.constant(0, i32).results[0]
        yield_region = self._single_block_region(
            arg_types=(i32,),
            terminator_factory=lambda args: scf.yield_(args[0]),
        )
        body = self._single_block_region(
            arg_types=(index, i32),
            terminator_factory=lambda args: scf.forall_in_parallel(
                scf.forall_yield(args[1], region=yield_region)
            ),
        )
        op = Operation.create(
            "scf.forall",
            operands=(lower, upper, step, shared),
            result_types=(index,),
            properties={"rank": 1, "shared_output_count": 1},
            regions=(body,),
        )

        with self.assertRaisesRegex(VerificationError, "result types"):
            verify_operation(op)


if __name__ == "__main__":
    unittest.main()
