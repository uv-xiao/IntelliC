import unittest

from intellic.ir.actions import MutationIntent, MutatorStage, PendingRecordGate, PipelineRun, passes
from intellic.ir.dialects import affine, arith, builtin, func, scf
from intellic.ir.syntax import Block, Builder, Operation, Region, i32, index


class ActionTests(unittest.TestCase):
    def test_canonicalize_records_mutation_before_mutator_applies_it(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            value = builder.insert(arith.constant(7, i32))
            zero = builder.insert(arith.constant(0, i32))
            add = builder.insert(arith.addi(value.results[0], zero.results[0]))
        run = PipelineRun(module)

        passes.canonicalize_greedy().run(run)

        self.assertEqual(block.operations[-1], add)
        self.assertEqual(len(run.db.query("MutationIntent")), 1)
        with self.assertRaisesRegex(ValueError, "pending records"):
            PendingRecordGate().run(run)

        MutatorStage().run(run)

        self.assertNotIn(add, block.operations)
        self.assertEqual(len(run.db.query("MutationApplied")), 1)
        PendingRecordGate().run(run)

    def test_cse_records_duplicate_erase_intent(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)

        intent = run.db.require("MutationIntent", duplicate.id).value
        self.assertEqual(intent.kind, "replace_uses_and_erase")

    def test_cse_replaces_duplicate_result_uses_before_erasing(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            representative = builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
            user = builder.insert(arith.addi(duplicate.results[0], representative.results[0]))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)
        intent = run.db.require("MutationIntent", duplicate.id).value

        self.assertEqual(intent.kind, "replace_uses_and_erase")
        self.assertIs(intent.replacement, representative.results[0])

        MutatorStage().run(run)

        self.assertNotIn(duplicate, block.operations)
        self.assertIs(user.operands[0], representative.results[0])
        self.assertEqual(duplicate.results[0].uses, ())
        self.assertTrue(
            any(use.owner is user and use.operand_index == 0 for use in representative.results[0].uses)
        )

    def test_cse_replacement_target_survives_symbol_dce_before_mutation(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            representative = builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
            two = builder.insert(arith.constant(2, i32))
            user = builder.insert(arith.addi(duplicate.results[0], two.results[0]))
            builder.insert(Operation.create("test.consume", operands=(user.results[0],)))
        run = PipelineRun(module)

        passes.common_subexpression_elimination().run(run)
        passes.symbol_dce_and_dead_code().run(run)

        self.assertEqual(run.db.query("MutationIntent", representative.id), ())

        MutatorStage().run(run)

        self.assertIn(representative, block.operations)
        self.assertNotIn(duplicate, block.operations)
        self.assertIs(user.operands[0], representative.results[0])
        self.assertTrue(
            any(use.owner is user and use.operand_index == 0 for use in representative.results[0].uses)
        )

    def test_constant_propagation_records_constant_facts(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(42, i32))
        run = PipelineRun(module)

        passes.sparse_constant_propagation().run(run)

        self.assertEqual(run.db.require("ValueConcrete", const.results[0].id).value, 42)

    def test_named_shared_passes_record_action_evidence(self) -> None:
        module = builtin.module(Region.from_block_list([Block()]))
        run = PipelineRun(module)

        for action in (
            passes.verify_structure(),
            passes.symbol_dce_and_dead_code(),
            passes.inline_single_call(),
            passes.loop_invariant_code_motion(),
            passes.lower_affine_to_scf(),
            passes.normalize_and_simplify_affine_loops(),
        ):
            action.run(run)

        action_names = [record.value["name"] for record in run.db.query("ActionRun")]
        self.assertIn("verify-structure", action_names)
        self.assertIn("inline-single-call", action_names)
        self.assertIn("lower-affine-to-scf", action_names)

    def test_symbol_dce_records_liveness_and_erases_unused_pure_ops(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            dead = builder.insert(arith.constant(9, i32))
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)

        self.assertEqual(run.db.require("DeadCodeCandidate", dead.id).value["reason"], "unused pure op")
        self.assertEqual(run.db.require("MutationIntent", dead.id).value.kind, "erase_op")

        MutatorStage().run(run)

        self.assertNotIn(dead, block.operations)

    def test_symbol_dce_erases_unused_private_function(self) -> None:
        module_block = Block()
        module = builtin.module(Region.from_block_list([module_block]))
        function_type = func.FunctionType(inputs=(i32,), results=(i32,))
        function_block = Block(arg_types=(i32,))
        function_region = Region.from_block_list([function_block])
        with Builder().insert_at_end(function_block) as builder:
            builder.insert(func.return_(function_block.arguments[0]))
        dead_function = func.func("dead_private", function_type, function_region)
        dead_function.properties["sym_visibility"] = "private"
        with Builder().insert_at_end(module_block) as builder:
            builder.insert(dead_function)
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)

        self.assertFalse(run.db.require("SymbolLiveness", dead_function.id).value["live"])
        self.assertEqual(run.db.require("DeadCodeCandidate", dead_function.id).value["reason"], "unused function")
        self.assertEqual(run.db.require("MutationIntent", dead_function.id).value.kind, "erase_op")

        MutatorStage().run(run)

        self.assertNotIn(dead_function, module_block.operations)

    def test_symbol_dce_preserves_called_private_function(self) -> None:
        module_block = Block()
        module = builtin.module(Region.from_block_list([module_block]))
        function_type = func.FunctionType(inputs=(i32,), results=(i32,))

        callee_block = Block(arg_types=(i32,))
        callee_region = Region.from_block_list([callee_block])
        with Builder().insert_at_end(callee_block) as builder:
            builder.insert(func.return_(callee_block.arguments[0]))
        callee = func.func("called_private", function_type, callee_region)
        callee.properties["sym_visibility"] = "private"

        caller_block = Block(arg_types=(i32,))
        caller_region = Region.from_block_list([caller_block])
        with Builder().insert_at_end(caller_block) as builder:
            call = builder.insert(func.call("called_private", (caller_block.arguments[0],), function_type))
            builder.insert(func.return_(call.results[0]))
        caller = func.func("main", function_type, caller_region)

        with Builder().insert_at_end(module_block) as builder:
            builder.insert(callee)
            builder.insert(caller)
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)

        self.assertTrue(run.db.require("SymbolLiveness", callee.id).value["live"])
        with self.assertRaises(KeyError):
            run.db.require("MutationIntent", callee.id)

    def test_inline_single_call_records_callgraph_and_inline_intent(self) -> None:
        module_block = Block()
        module = builtin.module(Region.from_block_list([module_block]))
        callee_type = func.FunctionType(inputs=(i32,), results=(i32,))

        callee_block = Block(arg_types=(i32,))
        callee_region = Region.from_block_list([callee_block])
        with Builder().insert_at_end(callee_block) as builder:
            builder.insert(func.return_(callee_block.arguments[0]))
        callee = func.func("identity", callee_type, callee_region)

        caller_block = Block(arg_types=(i32,))
        caller_region = Region.from_block_list([caller_block])
        with Builder().insert_at_end(caller_block) as builder:
            call = builder.insert(func.call("identity", (caller_block.arguments[0],), callee_type))
            builder.insert(func.return_(call.results[0]))
        caller = func.func("caller", callee_type, caller_region)

        with Builder().insert_at_end(module_block) as builder:
            builder.insert(callee)
            builder.insert(caller)
        run = PipelineRun(module)

        passes.inline_single_call().run(run)

        self.assertEqual(run.db.require("CallGraphEdge", call.id).value["callee"], callee.id)
        inline = run.db.require("InlineIntent", call.id).value
        self.assertEqual(inline["callee"], callee.id)
        self.assertEqual(inline["strategy"], "single-return-forward")

    def test_loop_invariant_code_motion_records_loop_scope_and_candidate(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            lower = builder.insert(arith.constant(0, index)).results[0]
            upper = builder.insert(arith.constant(8, index)).results[0]
            step = builder.insert(arith.constant(1, index)).results[0]

        body_block = Block(arg_types=(index,))
        body = Region.from_block_list([body_block])
        with Builder().insert_at_end(body_block) as builder:
            invariant = builder.insert(arith.constant(4, i32))
            builder.insert(scf.yield_())

        with Builder().insert_at_end(block) as builder:
            loop = builder.insert(scf.for_(lower, upper, step, body=body))
        run = PipelineRun(module)

        passes.loop_invariant_code_motion().run(run)

        self.assertEqual(run.db.require("LoopScope", loop.id).value["kind"], "scf.for")
        move = run.db.require("LoopInvariantCandidate", invariant.id).value
        self.assertEqual(move["loop"], loop.id)
        self.assertEqual(move["action"], "would_move_before_loop")

    def test_lower_affine_to_scf_records_dim_symbol_mapping_for_affine_apply(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            dim = builder.insert(arith.constant(3, index)).results[0]
            symbol = builder.insert(arith.constant(5, index)).results[0]
            affine_apply = builder.insert(
                affine.apply(affine.AffineMap(1, 1, ("d0 + s0",)), (dim,), (symbol,))
            )
        run = PipelineRun(module)

        passes.lower_affine_to_scf().run(run)

        mapping = run.db.require("AffineDimSymbolMapping", affine_apply.id).value
        expansion = run.db.require("AffineExpansion", affine_apply.id).value
        self.assertEqual(mapping["dims"], (dim.id,))
        self.assertEqual(mapping["symbols"], (symbol.id,))
        self.assertEqual(expansion["results"], ("d0 + s0",))

    def test_normalize_affine_loops_records_normalized_bounds(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        lower = affine.AffineMap(0, 0, ("0",))
        upper = affine.AffineMap(0, 0, ("16",))
        loop_body = Region.from_block_list([Block()])
        with Builder().insert_at_end(block) as builder:
            loop = builder.insert(affine.for_(lower, upper, 4, (), loop_body))
        run = PipelineRun(module)

        passes.normalize_and_simplify_affine_loops().run(run)

        bounds = run.db.require("AffineLoopBounds", loop.id).value
        band = run.db.require("AffineLoopBand", loop.id).value
        normalized = run.db.require("AffineNormalizedBounds", loop.id).value
        self.assertEqual(bounds["step"], 4)
        self.assertEqual(band["loops"], (loop.id,))
        self.assertEqual(normalized["lower"], ("0",))
        self.assertEqual(normalized["upper"], ("16",))

    def test_pending_record_gate_records_success_after_mutations_are_consumed(self) -> None:
        module = builtin.module(Region.from_block_list([Block()]))
        run = PipelineRun(module)

        PendingRecordGate().run(run)

        self.assertEqual(run.db.require("PendingRecordGate", module.id).value["status"], "passed")

    def test_mutator_rejects_stale_mutation_intent_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            stale = builder.insert(arith.constant(11, i32))
        run = PipelineRun(module)
        run.db.put("MutationIntent", stale.id, MutationIntent("erase_op", stale, reason="stale test"))
        block._operations.remove(stale)

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", stale.id).value
        self.assertEqual(rejection.intent.subject, stale)
        self.assertEqual(rejection.reason, "stale mutation subject")
        self.assertEqual(run.db.query("MutationIntent", stale.id), ())
        PendingRecordGate().run(run)

    def test_mutator_rejects_erasing_used_result_producer_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            used = builder.insert(arith.constant(13, i32))
            zero = builder.insert(arith.constant(0, i32))
            user = builder.insert(arith.addi(used.results[0], zero.results[0]))
        run = PipelineRun(module)
        run.db.put("MutationIntent", used.id, MutationIntent("erase_op", used, reason="unsafe test"))

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", used.id).value
        self.assertEqual(rejection.reason, "used result producer")
        self.assertIn(used, block.operations)
        self.assertIs(user.operands[0], used.results[0])
        self.assertEqual(run.db.query("MutationIntent", used.id), ())
        PendingRecordGate().run(run)


if __name__ == "__main__":
    unittest.main()
