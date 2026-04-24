import unittest

from intellic.examples.affine_tile import build_affine_tiled_access
from intellic.examples.sum_to_n import build_sum_to_n
from intellic.ir.actions import MutatorStage, PendingRecordGate, PipelineRun, passes
from intellic.ir.parser import parse_operation
from intellic.ir.semantics import TraceDB, execute_function
from intellic.ir.syntax import verify_operation
from intellic.ir.syntax.printer import print_operation


def operation_names(op):
    names = [op.name]
    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                names.extend(operation_names(child))
    return names


class ExampleTests(unittest.TestCase):
    def test_sum_to_n_runs_roundtrips_and_records_action_evidence(self) -> None:
        example = build_sum_to_n()

        verify_operation(example.operation)
        db = TraceDB()
        self.assertEqual(execute_function(example.operation, (5,), db), (10,))
        self.assertEqual(len(db.query("LoopIteration")), 5)

        text = print_operation(example.operation)
        parsed = parse_operation(text)
        self.assertEqual(operation_names(parsed), operation_names(example.operation))

        run = PipelineRun(example.operation)
        for action in (
            passes.verify_structure(),
            passes.canonicalize_greedy(),
            passes.common_subexpression_elimination(),
            passes.sparse_constant_propagation(),
            passes.symbol_dce_and_dead_code(),
            passes.inline_single_call(),
            passes.loop_invariant_code_motion(),
            passes.normalize_and_simplify_affine_loops(),
        ):
            action.run(run)
        MutatorStage().run(run)
        PendingRecordGate().run(run)

        action_names = [record.value["name"] for record in run.db.query("ActionRun")]
        self.assertIn("canonicalize-greedy", action_names)
        self.assertIn("loop-invariant-code-motion", action_names)
        self.assertEqual(run.db.require("ValueConcrete", example.zero_i.id).value, 0)

    def test_affine_tiled_access_records_scalar_and_vector_memory_facts(self) -> None:
        example = build_affine_tiled_access()

        verify_operation(example.module)
        text = print_operation(example.module)
        parsed = parse_operation(text)
        self.assertEqual(operation_names(parsed), operation_names(example.module))

        run = PipelineRun(example.module)
        passes.lower_affine_to_scf().run(run)

        accesses = run.db.query("AffineAccess")
        effects = [record.value["kind"] for record in run.db.query("MemoryEffect")]
        self.assertEqual(len(accesses), 4)
        self.assertEqual(effects.count("read"), 2)
        self.assertEqual(effects.count("write"), 2)
        self.assertEqual(run.db.require("AffineAccess", example.scalar_load.id).value["rank"], 2)
        self.assertEqual(run.db.require("AffineAccess", example.vector_store.id).value["kind"], "write")


if __name__ == "__main__":
    unittest.main()
