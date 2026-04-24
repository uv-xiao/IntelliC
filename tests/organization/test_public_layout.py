import unittest


class PublicLayoutTests(unittest.TestCase):
    def test_concrete_dialects_are_imported_from_top_level_dialects(self) -> None:
        from intellic.dialects import affine, arith, builtin, func, memref, scf, vector

        self.assertEqual(builtin.module.__module__, "intellic.dialects.builtin")
        self.assertEqual(arith.constant.__module__, "intellic.dialects.arith")
        self.assertEqual(func.func.__module__, "intellic.dialects.func")
        self.assertEqual(scf.for_.__module__, "intellic.dialects.scf")
        self.assertEqual(affine.AffineMap.__module__, "intellic.dialects.affine")
        self.assertEqual(memref.MemRefType.__module__, "intellic.dialects.memref")
        self.assertEqual(vector.VectorType.__module__, "intellic.dialects.vector")

    def test_concrete_passes_are_imported_from_top_level_actions(self) -> None:
        from intellic.actions import passes

        self.assertEqual(
            passes.common_subexpression_elimination.__module__,
            "intellic.actions.passes",
        )
        self.assertEqual(
            passes.normalize_and_simplify_affine_loops.__module__,
            "intellic.actions.passes",
        )


if __name__ == "__main__":
    unittest.main()
