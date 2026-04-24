import unittest

from intellic.actions import passes
from intellic.dialects import affine, arith, builtin, func, memref, scf
from intellic.ir.actions import CompilerAction, MutationIntent, MutatorStage, PendingRecordGate, PipelineRun
from intellic.ir.syntax import Attribute, Block, Builder, Operation, Region, i1, i32, index, verify_operation


class MutatorStageTests(unittest.TestCase):
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

    def test_mutator_rejects_self_replacement_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            subject = builder.insert(arith.constant(21, i32))
            zero = builder.insert(arith.constant(0, i32))
            user = builder.insert(arith.addi(subject.results[0], zero.results[0]))
        run = PipelineRun(module)
        run.db.put(
            "MutationIntent",
            subject.id,
            MutationIntent(
                "replace_uses_and_erase",
                subject,
                subject.results[0],
                reason="self replacement test",
            ),
        )

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", subject.id).value
        self.assertEqual(rejection.reason, "self replacement value")
        self.assertIn(subject, block.operations)
        self.assertIs(user.operands[0], subject.results[0])
        self.assertNoDetachedOperands(block)
        PendingRecordGate().run(run)

    def test_mutator_rejects_later_same_block_replacement_with_evidence(self) -> None:
        block = Block()
        module = builtin.module(Region.from_block_list([block]))
        with Builder().insert_at_end(block) as builder:
            old = builder.insert(arith.constant(1, i32))
            zero = builder.insert(arith.constant(0, i32))
            user = builder.insert(arith.addi(old.results[0], zero.results[0]))
            later = builder.insert(arith.constant(2, i32))
        run = PipelineRun(module)
        run.db.put(
            "MutationIntent",
            old.id,
            MutationIntent(
                "replace_uses_and_erase",
                old,
                later.results[0],
                reason="later replacement test",
            ),
        )

        MutatorStage().run(run)

        rejection = run.db.require("MutationRejected", old.id).value
        self.assertEqual(rejection.reason, "replacement does not dominate use")
        self.assertIn(old, block.operations)
        self.assertIs(user.operands[0], old.results[0])
        self.assertNoDetachedOperands(block)
        PendingRecordGate().run(run)

    def assertNoDetachedOperands(self, block: Block) -> None:
        operations = set(block.operations)
        for op in block.operations:
            for operand in op.operands:
                owner = getattr(operand, "owner", None)
                if isinstance(owner, Operation):
                    self.assertIn(owner, operations)


if __name__ == "__main__":
    unittest.main()
