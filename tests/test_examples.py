import unittest

from examples.affine_tile import build_affine_tiled_access
from examples.affine_stencil_tile import run_demo as run_affine_stencil_demo
from examples.common import ExampleRun, print_example_run
from examples.scf_piecewise_accumulate import run_demo as run_scf_piecewise_demo
from examples.sum_to_n import build_sum_to_n
from intellic.actions import passes
from intellic.ir.actions import MutatorStage, PendingRecordGate, PipelineRun
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


class ExampleCommonTests(unittest.TestCase):
    def test_example_run_records_structured_evidence_and_prints_sections(self) -> None:
        run = ExampleRun(
            name="demo",
            canonical_ir='"demo.op"() : () -> ()',
            parse_print_idempotent=True,
            semantic_result=(5,),
            action_names=("verify-structure",),
            relation_counts={"ActionRun": 1},
            mutation_applied_count=0,
            documented_gaps=("no gap",),
        )

        text = print_example_run(run)

        self.assertIn("== demo ==", text)
        self.assertIn("parse_print_idempotent: true", text)
        self.assertIn("semantic_result: (5,)", text)
        self.assertIn("actions: verify-structure", text)
        self.assertIn("ActionRun: 1", text)
        self.assertIn("documented_gaps:", text)


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
        self.assertEqual(text, print_operation(parsed))
        self.assertEqual(
            text,
            "\n".join(
                (
                    '"func.func"() <{function_type = #intellic.object<"intellic.dialects.func.FunctionType", {inputs = [!intellic.type<"index">], results = [!intellic.type<"i32">]}>, sym_name = "sum_to_n"}> ({',
                    "  ^bb0(%0: index):",
                    '    %1 = "arith.constant"() <{value = 0}> : () -> index',
                    '    %2 = "arith.constant"() <{value = 1}> : () -> index',
                    '    %3 = "arith.constant"() <{value = 0}> : () -> i32',
                    '    %4 = "scf.for"(%1, %0, %2, %3) <{iter_arg_count = 1}> ({',
                    "      ^bb1(%5: index, %6: i32):",
                    '        %7 = "arith.index_cast"(%5) <{to_type = !intellic.type<"i32">}> : (index) -> i32',
                    '        %8 = "arith.addi"(%6, %7) : (i32, i32) -> i32',
                    '        "scf.yield"(%8) : (i32) -> ()',
                    "    }) : (index, index, index, i32) -> i32",
                    '    "func.return"(%4) : (i32) -> ()',
                    "}) : () -> ()",
                )
            ),
        )

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
        self.assertEqual(text, print_operation(parsed))
        self.assertIn('"affine.vector_load"', text)
        self.assertIn('#intellic.object<"intellic.dialects.affine.AffineMap"', text)

        run = PipelineRun(example.module)
        passes.lower_affine_to_scf().run(run)

        accesses = run.db.query("AffineAccess")
        effects = [record.value["kind"] for record in run.db.query("MemoryEffect")]
        self.assertEqual(len(accesses), 4)
        self.assertEqual(effects.count("read"), 2)
        self.assertEqual(effects.count("write"), 2)
        self.assertEqual(run.db.require("AffineAccess", example.scalar_load.id).value["rank"], 2)
        self.assertEqual(run.db.require("AffineAccess", example.vector_store.id).value["kind"], "write")


class StrongExampleTests(unittest.TestCase):
    def test_scf_piecewise_accumulate_roundtrips_and_documents_if_execution_gap(self) -> None:
        run = run_scf_piecewise_demo()

        self.assertTrue(run.parse_print_idempotent)
        self.assertIn('"scf.if"', run.canonical_ir)
        self.assertIn('"scf.for"', run.canonical_ir)
        self.assertIn("sparse-constant-propagation", run.action_names)
        self.assertGreaterEqual(run.relation_counts["BranchReachability"], 2)
        self.assertGreaterEqual(run.relation_counts["ThenReachable"], 1)
        self.assertGreaterEqual(run.relation_counts["ElseReachable"], 1)
        self.assertIn("scf.if concrete execution is not implemented", run.documented_gaps)

    def test_affine_stencil_tile_records_accesses_and_lowering_evidence(self) -> None:
        run = run_affine_stencil_demo()

        self.assertTrue(run.parse_print_idempotent)
        self.assertIn('"affine.vector_load"', run.canonical_ir)
        self.assertIn('"affine.vector_store"', run.canonical_ir)
        self.assertIn('"affine.load"(%0, %5, %6, %3, %4)', run.canonical_ir)
        self.assertIn('"affine.store"(%11, %0, %5, %6, %3, %4)', run.canonical_ir)
        self.assertIn('"affine.vector_load"(%0, %5, %6, %3, %4)', run.canonical_ir)
        self.assertIn('"affine.vector_store"(%12, %0, %5, %6, %3, %4)', run.canonical_ir)
        self.assertIn("lower-affine-to-scf", run.action_names)
        self.assertEqual(run.relation_counts["UniqueAffineAccess"], 7)
        self.assertEqual(run.relation_counts["UniqueMemoryEffect"], 7)
        self.assertEqual(run.relation_counts["ReadAccess"], 4)
        self.assertEqual(run.relation_counts["WriteAccess"], 3)
        self.assertEqual(run.relation_counts["CSEReadObserved"], 4)
        self.assertEqual(run.relation_counts["CSESkipSideEffect"], 3)
        self.assertEqual(run.relation_counts["UniqueAffineExpansion"], 9)
        self.assertIn(
            "affine concrete memory execution is not implemented",
            run.documented_gaps,
        )


if __name__ == "__main__":
    unittest.main()
