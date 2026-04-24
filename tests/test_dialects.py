import unittest

from intellic.ir.dialects import affine, arith, builtin, func, memref, scf, vector
from intellic.ir.syntax import Block, Operation, Region, Type, i32, index


class DialectTests(unittest.TestCase):
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
