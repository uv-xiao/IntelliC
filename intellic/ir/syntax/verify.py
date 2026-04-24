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
                verify_operation(child)
