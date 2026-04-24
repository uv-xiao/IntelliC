import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class PipelineTests(unittest.TestCase):
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
        evidence = run.db.require("RewriteEvidence", add.id).value
        self.assertEqual(evidence["action"], "canonicalize-greedy")
        self.assertEqual(evidence["replacement"], value.results[0].id)
        with self.assertRaisesRegex(ValueError, "pending records"):
            PendingRecordGate().run(run)

        MutatorStage().run(run)

        self.assertNotIn(add, block.operations)
        self.assertEqual(len(run.db.query("MutationApplied")), 1)
        PendingRecordGate().run(run)

    def test_verify_structure_records_diagnostic_and_evidence_link(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        run = PipelineRun(module)

        passes.verify_structure().run(run)

        diagnostic = run.db.require("Diagnostic", module.id).value
        evidence = run.db.require("EvidenceLink", module.id).value
        self.assertEqual(diagnostic["action"], "verify-structure")
        self.assertEqual(diagnostic["severity"], "info")
        self.assertEqual(evidence["action"], "verify-structure")
        self.assertEqual(evidence["subject"], module.id)

    def test_dce_before_cse_rejects_replacement_to_erased_representative(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            representative = builder.insert(arith.constant(1, i32))
            duplicate = builder.insert(arith.constant(1, i32))
            two = builder.insert(arith.constant(2, i32))
            user = builder.insert(arith.addi(duplicate.results[0], two.results[0]))
            builder.insert(Operation.create("test.consume", operands=(user.results[0],)))
        run = PipelineRun(module)

        passes.symbol_dce_and_dead_code().run(run)
        passes.common_subexpression_elimination().run(run)

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", duplicate.id).value
        self.assertEqual(rejection.reason, "stale replacement value")
        self.assertNotIn(representative, block.operations)
        self.assertIn(duplicate, block.operations)
        self.assertIs(user.operands[0], duplicate.results[0])
        self.assertNoDetachedOperands(block)

    def assertNoDetachedOperands(self, block: Block) -> None:
        operations = set(block.operations)
        for op in block.operations:
            for operand in op.operands:
                owner = getattr(operand, "owner", None)
                if isinstance(owner, Operation):
                    self.assertIn(owner, operations)


if __name__ == "__main__":
    unittest.main()
