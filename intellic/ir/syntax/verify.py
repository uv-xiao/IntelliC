from __future__ import annotations

from collections.abc import Callable

from .operation import Operation


class VerificationError(Exception):
    """Raised when syntax structure violates ownership or use-list invariants."""


OperationVerifier = Callable[[Operation], None]

_OPERATION_VERIFIERS: dict[str, OperationVerifier] = {}


def register_operation_verifier(name_prefix: str, verifier: OperationVerifier) -> None:
    if not name_prefix:
        raise ValueError("operation verifier prefix must be non-empty")
    _OPERATION_VERIFIERS[name_prefix] = verifier


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
    _verify_dialect_contract(op)

    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                verify_operation(child)


def _verify_dialect_contract(op: Operation) -> None:
    for name_prefix, verifier in _OPERATION_VERIFIERS.items():
        if not op.name.startswith(name_prefix):
            continue
        try:
            verifier(op)
        except (TypeError, ValueError) as exc:
            raise VerificationError(f"{op.name}: {exc}") from exc
