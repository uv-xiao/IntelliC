import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class TransformPassTests(unittest.TestCase):
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
        mapping = run.db.require("ClonedRegionMapping", call.id).value
        self.assertEqual(inline["callee"], callee.id)
        self.assertEqual(inline["strategy"], "single-return-forward")
        self.assertEqual(mapping["strategy"], "single-return-forward")
        self.assertEqual(mapping["call_results"], (call.results[0].id,))
        self.assertEqual(mapping["replacements"], (caller_block.arguments[0].id,))

    def test_inline_single_call_mutator_applies_block_argument_forwarding(self) -> None:
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
            ret = builder.insert(func.return_(call.results[0]))
        caller = func.func("caller", callee_type, caller_region)

        with Builder().insert_at_end(module_block) as builder:
            builder.insert(callee)
            builder.insert(caller)
        run = PipelineRun(module)

        passes.inline_single_call().run(run)
        MutatorStage().run(run)

        self.assertNotIn(call, caller_block.operations)
        self.assertIs(ret.operands[0], caller_block.arguments[0])
        self.assertEqual(run.db.query("MutationRejected", call.id), ())
        PendingRecordGate().run(run)

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
        side_effect = run.db.require("SideEffectFact", invariant.id).value
        moved = run.db.require("MovedOpEvidence", invariant.id).value
        self.assertEqual(move["loop"], loop.id)
        self.assertEqual(move["action"], "would_move_before_loop")
        self.assertEqual(side_effect["effect"], "none")
        self.assertEqual(moved["target"], "before-loop")
        self.assertEqual(moved["status"], "record-only")

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


if __name__ == "__main__":
    unittest.main()
