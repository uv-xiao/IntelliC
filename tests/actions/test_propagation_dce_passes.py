import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class PropagationDCEPassTests(unittest.TestCase):
    def test_constant_propagation_records_constant_facts(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            const = builder.insert(arith.constant(42, i32))
        run = PipelineRun(module)

        passes.sparse_constant_propagation().run(run)

        self.assertEqual(run.db.require("ValueConcrete", const.results[0].id).value, 42)
        value_range = run.db.require("ValueRange", const.results[0].id).value
        self.assertEqual(value_range["min"], 42)
        self.assertEqual(value_range["max"], 42)

    def test_constant_propagation_records_branch_and_region_reachability(self) -> None:
        block = Block()
        then_block = Block()
        else_block = Block()
        then_region = Region.from_block_list([then_block])
        else_region = Region.from_block_list([else_block])
        with Builder().insert_at_end(then_block) as builder:
            builder.insert(scf.yield_())
        with Builder().insert_at_end(else_block) as builder:
            builder.insert(scf.yield_())
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            condition = builder.insert(arith.constant(1, i1))
            if_op = builder.insert(
                scf.if_(condition.results[0], then_region=then_region, else_region=else_region)
            )
        run = PipelineRun(module)

        passes.sparse_constant_propagation().run(run)

        branch = run.db.require("BranchReachability", if_op.id).value
        then_reachability = run.db.require("RegionReachability", then_region.id).value
        else_reachability = run.db.require("RegionReachability", else_region.id).value
        self.assertTrue(branch["then_reachable"])
        self.assertFalse(branch["else_reachable"])
        self.assertTrue(then_reachability["reachable"])
        self.assertFalse(else_reachability["reachable"])

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


if __name__ == "__main__":
    unittest.main()
