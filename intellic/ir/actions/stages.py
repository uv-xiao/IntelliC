from __future__ import annotations

from .mutation import MutationApplied, MutationIntent, MutationRejected
from .pipeline import PipelineRun


class MutatorStage:
    def run(self, run: PipelineRun) -> None:
        for record in tuple(run.db.query("MutationIntent")):
            intent = record.value
            if not isinstance(intent, MutationIntent):
                continue
            rejection_reason = self._rejection_reason(intent)
            if rejection_reason is not None:
                run.db.put("MutationRejected", intent.subject.id, MutationRejected(intent, rejection_reason))
                run.db.retract(record.id, reason="rejected")
                continue
            self._apply_intent(intent)
            run.db.put("MutationApplied", intent.subject.id, MutationApplied(intent))
            run.db.retract(record.id, reason="applied")

    def _rejection_reason(self, intent: MutationIntent) -> str | None:
        parent = intent.subject.parent
        if parent is None:
            return "stale mutation subject"
        operations = getattr(parent, "_operations", None)
        if operations is None or intent.subject not in operations:
            return "stale mutation subject"
        return None

    def _apply_intent(self, intent: MutationIntent) -> None:
        parent = intent.subject.parent
        if parent is None:
            raise ValueError("cannot mutate detached operation")
        operations = parent._operations
        index = operations.index(intent.subject)
        if intent.kind == "erase_op":
            intent.subject.erase_operand_uses()
            del operations[index]
            return
        if intent.kind == "replace_uses_and_erase":
            if intent.replacement is None:
                raise ValueError("replacement mutation requires value")
            for result in intent.subject.results:
                for use in tuple(result.uses):
                    use.owner.replace_operand(use.operand_index, intent.replacement)
            intent.subject.erase_operand_uses()
            del operations[index]
            return
        raise ValueError(f"unknown mutation kind: {intent.kind}")


class PendingRecordGate:
    def run(self, run: PipelineRun) -> None:
        pending = run.db.query("MutationIntent")
        if pending:
            raise ValueError(f"pending records remain: {len(pending)}")
        run.db.put("PendingRecordGate", run.module.id, {"status": "passed"})
