from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from intellic.ir.syntax import Operation

from .pipeline import PipelineRun


@dataclass(frozen=True)
class CompilerAction:
    name: str
    apply: Callable[[PipelineRun], None]

    def run(self, run: PipelineRun) -> None:
        run.db.put("ActionRun", self.name, {"name": self.name})
        before = _syntax_snapshot(run.module)
        apply_error: BaseException | None = None
        try:
            self.apply(run)
        except BaseException as exc:
            apply_error = exc
        finally:
            after = _syntax_snapshot(run.module)
            violation = _direct_mutation_violation(before, after)
            if violation is not None:
                run.db.put("DirectMutationViolation", self.name, violation)
                if apply_error is None:
                    raise ValueError(f"direct syntax mutation in action {self.name}")
            if apply_error is not None:
                raise apply_error


def _syntax_snapshot(root: Operation) -> dict[str, dict[object, object]]:
    operations: dict[object, object] = {}
    blocks: dict[object, object] = {}
    uses: dict[object, object] = {}
    _collect_syntax(root, operations, blocks, uses)
    return {"operations": operations, "blocks": blocks, "uses": uses}


def _collect_syntax(
    op: Operation,
    operations: dict[object, object],
    blocks: dict[object, object],
    uses: dict[object, object],
) -> None:
    operations[op.id] = {
        "operands": tuple(operand.id for operand in op.operands),
        "parent": getattr(op.parent, "id", None),
        "properties": dict(op.properties),
        "attributes": dict(op.attributes),
    }
    for result in op.results:
        uses[result.id] = tuple((use.owner.id, use.operand_index) for use in result.uses)
    for region in op.regions:
        for block in region.blocks:
            blocks[block.id] = tuple(child.id for child in block.operations)
            for child in block.operations:
                _collect_syntax(child, operations, blocks, uses)


def _direct_mutation_violation(
    before: dict[str, dict[object, object]],
    after: dict[str, dict[object, object]],
) -> dict[str, object] | None:
    for op_id, before_op in before["operations"].items():
        after_op = after["operations"].get(op_id)
        if after_op is None:
            return {"kind": "operation_removed", "operation": op_id}
        if before_op["operands"] != after_op["operands"]:
            before_operands = before_op["operands"]
            after_operands = after_op["operands"]
            for index, before_operand in enumerate(before_operands):
                after_operand = after_operands[index] if index < len(after_operands) else None
                if before_operand != after_operand:
                    return {
                        "kind": "operand_changed",
                        "operation": op_id,
                        "operand_index": index,
                        "before": before_operand,
                        "after": after_operand,
                    }
            return {"kind": "operand_count_changed", "operation": op_id}
        if before_op["parent"] != after_op["parent"]:
            return {
                "kind": "parent_changed",
                "operation": op_id,
                "before": before_op["parent"],
                "after": after_op["parent"],
            }
        if before_op["properties"] != after_op["properties"]:
            return {
                "kind": "properties_changed",
                "operation": op_id,
                "before": before_op["properties"],
                "after": after_op["properties"],
            }
        if before_op["attributes"] != after_op["attributes"]:
            return {
                "kind": "attributes_changed",
                "operation": op_id,
                "before": before_op["attributes"],
                "after": after_op["attributes"],
            }
    for block_id, before_ops in before["blocks"].items():
        after_ops = after["blocks"].get(block_id)
        if before_ops != after_ops:
            return {"kind": "block_operations_changed", "block": block_id}
    for value_id, before_uses in before["uses"].items():
        after_uses = after["uses"].get(value_id)
        if before_uses != after_uses:
            return {
                "kind": "uses_changed",
                "value": value_id,
                "before": before_uses,
                "after": after_uses,
            }
    if set(before["operations"]) != set(after["operations"]):
        return {"kind": "operation_set_changed"}
    if set(before["blocks"]) != set(after["blocks"]):
        return {"kind": "block_set_changed"}
    return None
