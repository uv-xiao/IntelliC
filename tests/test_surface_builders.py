import unittest

from intellic.ir.syntax import Type, i32, index
from intellic.surfaces.api import arith, func, scf


def walk_names(op):
    names = [op.name]
    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                names.extend(walk_names(child))
    return names


class SurfaceBuilderTests(unittest.TestCase):
    def test_ir_function_builds_sum_to_n_with_evidence(self) -> None:
        @func.ir_function
        def sum_to_n(n: index) -> i32:
            zero_i = arith.constant(0, index)
            one_i = arith.constant(1, index)
            zero = arith.constant(0, i32)

            with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
                i, total = loop.arguments
                total_next = arith.addi(total, arith.index_cast(i, i32))
                scf.yield_(total_next)

            return loop.results[0]

        names = walk_names(sum_to_n.operation)

        self.assertEqual(sum_to_n.operation.name, "func.func")
        self.assertIn("scf.for", names)
        self.assertIn("func.return", names)
        self.assertIn("arith.index_cast", names)
        self.assertIn("builder:func.func:sum_to_n", sum_to_n.evidence)
        self.assertIn("builder:scf.for", sum_to_n.evidence)

    def test_builder_rejects_call_without_insertion_point(self) -> None:
        with self.assertRaisesRegex(ValueError, "no active insertion point"):
            arith.constant(0, i32)

    def test_ir_function_rejects_missing_annotations(self) -> None:
        with self.assertRaisesRegex(TypeError, "annotation"):

            @func.ir_function
            def bad(x):
                return x

    def test_symbolic_value_rejects_host_bool(self) -> None:
        with self.assertRaisesRegex(TypeError, "symbolic IR value"):

            @func.ir_function
            def identity(x: i32) -> i32:
                if x:
                    return x
                return x


if __name__ == "__main__":
    unittest.main()
