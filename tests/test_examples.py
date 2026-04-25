from pathlib import Path
import unittest

from examples.affine_stencil_tile import (
    build_example as build_affine_stencil_example,
)
from examples.affine_stencil_tile import run_demo as run_affine_stencil_demo
from examples.action_cleanup_pipeline import run_demo as run_action_cleanup_demo
from examples.common import ExampleRun, print_example_run
from examples.scf_piecewise_accumulate import run_demo as run_scf_piecewise_demo
from examples.sum_to_n import build_sum_to_n
from examples.sum_to_n import run_demo as run_sum_to_n_demo
from intellic.actions import passes
from intellic.ir.actions import MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.semantics import TraceDB, execute_function
from intellic.ir.syntax import verify_operation
from intellic.ir.syntax.printer import print_operation


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


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
    def test_examples_readme_describes_runnable_showcase_modules(self) -> None:
        readme = EXAMPLES_DIR / "README.md"

        self.assertTrue(readme.exists())
        text = readme.read_text(encoding="utf-8")
        for module in (
            "sum_to_n",
            "scf_piecewise_accumulate",
            "affine_stencil_tile",
            "action_cleanup_pipeline",
        ):
            self.assertIn(f"python -m examples.{module}", text)
        self.assertIn("parse/print", text)
        self.assertIn("semantic execution", text)
        self.assertIn("action evidence", text)

    def test_old_affine_tile_example_is_removed(self) -> None:
        self.assertFalse((EXAMPLES_DIR / "affine_tile.py").exists())

    def test_sum_to_n_runs_roundtrips_and_records_action_evidence(self) -> None:
        example = build_sum_to_n()
        demo = run_sum_to_n_demo()

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
        self.assertTrue(demo.parse_print_idempotent)
        self.assertEqual(demo.semantic_result, (10,))
        self.assertEqual(demo.semantic_records["LoopIteration"], 5)
        self.assertEqual(demo.semantic_records["Call"], 0)
        self.assertGreaterEqual(demo.semantic_records["Evaluated"], 10)
        self.assertIn("canonicalize-greedy", demo.action_names)
        self.assertIn("loop-invariant-code-motion", demo.action_names)
        self.assertGreaterEqual(demo.relation_counts["ValueConcrete"], 2)
        self.assertIn('"scf.for"', demo.canonical_ir)


class StrongExampleTests(unittest.TestCase):
    def test_action_cleanup_pipeline_runs_actions_and_preserves_semantics(self) -> None:
        run = run_action_cleanup_demo()

        self.assertTrue(run.parse_print_idempotent)
        self.assertEqual(run.semantic_result, (5,))
        self.assertIn("canonicalize-greedy", run.action_names)
        self.assertIn("common-subexpression-elimination", run.action_names)
        self.assertIn("symbol-dce-and-dead-code", run.action_names)
        self.assertIn("inline-single-call", run.action_names)
        self.assertNotIn("CallGraphEdge", run.relation_counts)
        self.assertNotIn("SymbolLiveness", run.relation_counts)
        self.assertGreaterEqual(run.relation_counts["MutationApplied"], 3)
        self.assertGreaterEqual(run.mutation_applied_count, 3)
        self.assertGreaterEqual(run.relation_counts["HistoricalCallGraphEdgeRecords"], 1)
        self.assertGreaterEqual(run.relation_counts["HistoricalSymbolLivenessRecords"], 1)
        self.assertEqual(run.relation_counts["FinalFuncCallOps"], 0)
        self.assertEqual(run.relation_counts["FinalIdentitySymbols"], 0)
        self.assertEqual(run.relation_counts["FinalDeadPrivateSymbols"], 0)
        self.assertEqual(run.relation_counts["FinalZeroConstants"], 0)
        self.assertIsNotNone(run.final_ir)
        self.assertNotIn('"func.call"', run.final_ir)
        self.assertNotIn("dead_private", run.final_ir)
        self.assertNotIn("identity", run.final_ir)
        self.assertNotIn("value = 0", run.final_ir)

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
        example = build_affine_stencil_example()
        run = run_affine_stencil_demo()

        bounded_dims = (example.min_bound.results[0], example.max_bound.results[0])
        self.assertEqual(
            [op.name for op in example.memory_ops],
            [
                "affine.load",
                "affine.load",
                "affine.load",
                "affine.store",
                "affine.store",
                "affine.vector_load",
                "affine.vector_store",
            ],
        )
        for op in example.memory_ops:
            if op.name in {"affine.load", "affine.vector_load"}:
                self.assertEqual(op.operands[1:3], bounded_dims)
            else:
                self.assertEqual(op.operands[2:4], bounded_dims)

        self.assertTrue(run.parse_print_idempotent)
        self.assertIn('"affine.vector_load"', run.canonical_ir)
        self.assertIn('"affine.vector_store"', run.canonical_ir)
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
