import unittest

from intellic.ir.dialects import affine, arith, builtin, func, memref, scf, vector
from intellic.ir.syntax import Block, Builder, Operation, Region, Type, i1, i32, index


class DialectTests(unittest.TestCase):
    def _single_block_region(self, arg_types=(), terminator_factory=None) -> Region:
        region = Region.from_block_list([Block(arg_types=arg_types)])
        if terminator_factory is not None:
            with scf.body_builder(region) as builder:
                builder.insert(terminator_factory(region.blocks[0].arguments))
        return region

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

    def test_affine_map_apply_and_memory_ops_verify_types(self) -> None:
        idx0 = arith.constant(0, index).results[0]
        idx1 = arith.constant(1, index).results[0]
        f32 = Type("f32")
        memref_type = memref.MemRefType(element_type=f32, shape=(None,))
        memref_value = Operation.create("test.arg", result_types=(memref_type,)).results[0]
        map_ = affine.AffineMap(dim_count=1, symbol_count=1, results=("d0 + s0",))

        applied = affine.apply(map_, dims=(idx0,), symbols=(idx1,))
        loaded = affine.load(memref_value, map_, dims=(idx0,), symbols=(idx1,))
        stored = affine.store(loaded.results[0], memref_value, map_, dims=(idx0,), symbols=(idx1,))

        self.assertEqual(applied.results[0].type, index)
        self.assertEqual(loaded.results[0].type, f32)
        self.assertEqual(stored.results, ())

        with self.assertRaisesRegex(ValueError, "dimension count"):
            affine.apply(map_, dims=(), symbols=(idx1,))

        with self.assertRaisesRegex(ValueError, "rank"):
            affine.load(memref_value, affine.AffineMap(2, 0, ("d0", "d1")), dims=(idx0, idx1), symbols=())

    def test_vector_type_requires_static_shape_and_matching_element(self) -> None:
        f32 = Type("f32")
        vec = vector.VectorType(element_type=f32, shape=(4,))
        mem = memref.MemRefType(element_type=f32, shape=(None,))
        mem_value = Operation.create("test.arg", result_types=(mem,)).results[0]
        idx = arith.constant(0, index).results[0]
        map_ = affine.AffineMap(1, 0, ("d0",))

        loaded = affine.vector_load(mem_value, map_, dims=(idx,), symbols=(), vector_type=vec)

        self.assertEqual(loaded.results[0].type, vec)

        with self.assertRaisesRegex(ValueError, "static"):
            vector.VectorType(element_type=f32, shape=(None,))

        with self.assertRaisesRegex(TypeError, "element type"):
            affine.vector_load(
                mem_value,
                map_,
                dims=(idx,),
                symbols=(),
                vector_type=vector.VectorType(element_type=i32, shape=(4,)),
            )


if __name__ == "__main__":
    unittest.main()
