from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from intellic.ir.syntax import Operation
from intellic.ir.syntax.mutation_guard import GuardedDict, GuardedList, direct_mutation_guard

from .pipeline import PipelineRun


@dataclass(frozen=True)
class CompilerAction:
    name: str
    apply: Callable[[PipelineRun], None]

    def run(self, run: PipelineRun) -> None:
        run.db.put("ActionRun", self.name, {"name": self.name})
        before = _syntax_snapshot(run.module)
        apply_error: BaseException | None = None
        with direct_mutation_guard() as attempts:
            try:
                self.apply(run)
            except BaseException as exc:
                apply_error = exc
            finally:
                after = _syntax_snapshot(run.module)
                violation = _direct_mutation_violation(before, after)
                if violation is None and attempts:
                    violation = {
                        "kind": "mutation_attempt",
                        "attempts": tuple(attempt["kind"] for attempt in attempts),
                        "details": tuple(attempts),
                    }
                if violation is not None:
                    _restore_syntax(before, after)
                    run.db.put("DirectMutationViolation", self.name, violation)
                    if apply_error is None:
                        raise ValueError(f"direct syntax mutation in action {self.name}")
                if apply_error is not None:
                    raise apply_error


def _syntax_snapshot(root: Operation) -> dict[str, dict[object, object]]:
    operations: dict[object, object] = {}
    regions: dict[object, object] = {}
    blocks: dict[object, object] = {}
    uses: dict[object, object] = {}
    _collect_syntax(root, operations, regions, blocks, uses)
    return {"operations": operations, "regions": regions, "blocks": blocks, "uses": uses}


def _collect_syntax(
    op: Operation,
    operations: dict[object, object],
    regions: dict[object, object],
    blocks: dict[object, object],
    uses: dict[object, object],
) -> None:
    operations[op.id] = {
        "object": op,
        "operands": tuple(operand.id for operand in op.operands),
        "operands_guarded": isinstance(op.operands, tuple),
        "operand_values": tuple(op.operands),
        "result_values": op.results,
        "region_values": op.regions,
        "successor_values": op.successors,
        "parent": getattr(op.parent, "id", None),
        "parent_object": op.parent,
        "properties_guarded": isinstance(op.properties, GuardedDict),
        "properties_object": op.properties,
        "properties": dict(op.properties),
        "attributes_guarded": isinstance(op.attributes, GuardedDict),
        "attributes_object": op.attributes,
        "attributes": dict(op.attributes),
    }
    for result in op.results:
        uses[result.id] = _value_uses_snapshot(result)
    for region in op.regions:
        regions[region.id] = {
            "object": region,
            "parent": getattr(region.parent, "id", None),
            "parent_object": region.parent,
            "blocks_guarded": isinstance(region._blocks, GuardedList),
            "blocks": tuple(region.blocks),
            "block_ids": tuple(block.id for block in region.blocks),
        }
        for block in region.blocks:
            blocks[block.id] = {
                "object": block,
                "parent": getattr(block.parent, "id", None),
                "parent_object": block.parent,
                "operations_guarded": isinstance(block._operations, GuardedList),
                "operations": tuple(block.operations),
                "operation_ids": tuple(child.id for child in block.operations),
            }
            for argument in block.arguments:
                uses[argument.id] = _value_uses_snapshot(argument)
            for child in block.operations:
                _collect_syntax(child, operations, regions, blocks, uses)


def _value_uses_snapshot(value) -> dict[str, object]:
    return {
        "object": value,
        "uses": tuple(value.uses),
        "use_ids": tuple((use.owner.id, use.operand_index) for use in value.uses),
    }


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
        if (
            not after_op["operands_guarded"]
            or not after_op["properties_guarded"]
            or not after_op["attributes_guarded"]
        ):
            return {"kind": "operation_storage_changed", "operation": op_id}
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
        if after_ops is not None and before_ops["parent"] != after_ops["parent"]:
            return {
                "kind": "block_parent_changed",
                "block": block_id,
                "before": before_ops["parent"],
                "after": after_ops["parent"],
            }
        if after_ops is not None and not after_ops["operations_guarded"]:
            return {"kind": "block_storage_changed", "block": block_id}
        if after_ops is None or before_ops["operation_ids"] != after_ops["operation_ids"]:
            return {"kind": "block_operations_changed", "block": block_id}
    for region_id, before_blocks in before["regions"].items():
        after_blocks = after["regions"].get(region_id)
        if after_blocks is not None and before_blocks["parent"] != after_blocks["parent"]:
            return {
                "kind": "region_parent_changed",
                "region": region_id,
                "before": before_blocks["parent"],
                "after": after_blocks["parent"],
            }
        if after_blocks is not None and not after_blocks["blocks_guarded"]:
            return {"kind": "region_storage_changed", "region": region_id}
        if after_blocks is None or before_blocks["block_ids"] != after_blocks["block_ids"]:
            return {"kind": "region_blocks_changed", "region": region_id}
    for value_id, before_uses in before["uses"].items():
        after_uses = after["uses"].get(value_id)
        if after_uses is None or before_uses["use_ids"] != after_uses["use_ids"]:
            return {
                "kind": "uses_changed",
                "value": value_id,
                "before": before_uses["use_ids"],
                "after": after_uses["use_ids"] if after_uses is not None else None,
            }
    if set(before["operations"]) != set(after["operations"]):
        return {"kind": "operation_set_changed"}
    if set(before["blocks"]) != set(after["blocks"]):
        return {"kind": "block_set_changed"}
    if set(before["regions"]) != set(after["regions"]):
        return {"kind": "region_set_changed"}
    return None


def _restore_syntax(
    snapshot: dict[str, dict[object, object]],
    after: dict[str, dict[object, object]] | None = None,
) -> None:
    for region_data in snapshot["regions"].values():
        region = region_data["object"]
        region.parent = region_data["parent_object"]
        region._blocks.clear()
        region._blocks.extend(region_data["blocks"])
    for block_data in snapshot["blocks"].values():
        block = block_data["object"]
        block.parent = block_data["parent_object"]
        block._operations.clear()
        block._operations.extend(block_data["operations"])
    for op_data in snapshot["operations"].values():
        op = op_data["object"]
        op.parent = op_data["parent_object"]
        op.operands = op_data["operand_values"]
        op.results = op_data["result_values"]
        op.regions = op_data["region_values"]
        op.successors = op_data["successor_values"]
        _restore_guarded_dict(op_data["properties_object"], op_data["properties"])
        _restore_guarded_dict(op_data["attributes_object"], op_data["attributes"])
        op.properties = op_data["properties_object"]
        op.attributes = op_data["attributes_object"]
    for use_data in snapshot["uses"].values():
        value = use_data["object"]
        value._uses = use_data["uses"]
    if after is not None:
        _detach_removed_syntax(snapshot, after)


def _detach_removed_syntax(
    snapshot: dict[str, dict[object, object]],
    after: dict[str, dict[object, object]],
) -> None:
    for op_id, op_data in after["operations"].items():
        if op_id not in snapshot["operations"]:
            op_data["object"].parent = None
    for block_id, block_data in after["blocks"].items():
        if block_id not in snapshot["blocks"]:
            block_data["object"].parent = None
    for region_id, region_data in after["regions"].items():
        if region_id not in snapshot["regions"]:
            region_data["object"].parent = None


def _restore_guarded_dict(target: GuardedDict, values: dict[object, object]) -> None:
    target.clear()
    target.update(values)
