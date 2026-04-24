from __future__ import annotations

from .operation import Operation


class VerificationError(Exception):
    """Raised when syntax structure violates ownership or use-list invariants."""


def verify_operation(op: Operation) -> None:
    for result_index, result in enumerate(op.results):
        if result.owner is not op:
            raise VerificationError(f"result {result_index} has wrong owner")
        if result.index != result_index:
            raise VerificationError(f"result {result_index} has wrong index")

    for operand_index, operand in enumerate(op.operands):
        if not any(use.owner is op and use.operand_index == operand_index for use in operand.uses):
            raise VerificationError(f"operand {operand_index} is missing use record")

    for region in op.regions:
        if region.parent is not op:
            raise VerificationError("region has wrong parent")
        for block in region.blocks:
            if block.parent is not region:
                raise VerificationError("block has wrong parent")
            for child in block.operations:
                if child.parent is not block:
                    raise VerificationError("operation has wrong parent")
    _verify_scf_terminator_context(op)
    _verify_dialect_contract(op)

    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                verify_operation(child)


def _verify_dialect_contract(op: Operation) -> None:
    if not op.name.startswith("scf."):
        return
    from intellic.ir.dialects import scf

    try:
        scf.verify_operation_contract(op)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"{op.name}: {exc}") from exc


def _verify_scf_terminator_context(op: Operation) -> None:
    if op.name == "scf.yield":
        _require_last_in_block(op)
        owner = _containing_operation(op)
        region = op.parent.parent
        if owner.name in ("scf.if", "scf.for", "scf.execute_region", "scf.index_switch"):
            if region in owner.regions:
                return
        if owner.name == "scf.while" and len(owner.regions) > 1 and region is owner.regions[1]:
            return
        if owner.name == "scf.forall.in_parallel" and region in owner.regions:
            return
        raise VerificationError("scf.yield has invalid parent context")

    if op.name == "scf.condition":
        _require_last_in_block(op)
        owner = _containing_operation(op)
        region = op.parent.parent
        if owner.name == "scf.while" and owner.regions and region is owner.regions[0]:
            return
        raise VerificationError("scf.condition has invalid parent context")

    if op.name == "scf.reduce.return":
        _require_last_in_block(op)
        owner = _containing_operation(op)
        region = op.parent.parent
        if owner.name == "scf.reduce" and region in owner.regions:
            return
        raise VerificationError("scf.reduce.return has invalid parent context")

    if op.name == "scf.reduce":
        _require_last_in_block(op)
        owner = _containing_operation(op)
        region = op.parent.parent
        if owner.name == "scf.parallel" and owner.regions and region is owner.regions[0]:
            return
        raise VerificationError("scf.reduce has invalid parent context")

    if op.name == "scf.forall.in_parallel":
        _require_last_in_block(op)
        owner = _containing_operation(op)
        region = op.parent.parent
        if owner.name == "scf.forall" and owner.regions and region is owner.regions[0]:
            return
        raise VerificationError("scf.forall.in_parallel has invalid parent context")


def _require_last_in_block(op: Operation) -> None:
    block = op.parent
    if block is None or not hasattr(block, "operations"):
        raise VerificationError(f"{op.name} has no parent block")
    if not block.operations or block.operations[-1] is not op:
        raise VerificationError(f"{op.name} must be last in its block")


def _containing_operation(op: Operation) -> Operation:
    block = op.parent
    region = block.parent
    owner = region.parent
    if not isinstance(owner, Operation):
        raise VerificationError(f"{op.name} has invalid parent context")
    return owner
