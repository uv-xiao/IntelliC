import unittest

from intellic.dialects import affine, arith, builtin, func, memref, scf, vector
from intellic.ir.syntax import Block, Builder, Operation, Region, Type, VerificationError, i1, i32, index, verify_operation


class AffineVectorTests(unittest.TestCase):
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
