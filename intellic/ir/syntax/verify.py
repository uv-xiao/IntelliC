from __future__ import annotations

from collections.abc import Callable

from .operation import Operation


class VerificationError(Exception):
    """Raised when syntax structure violates ownership or use-list invariants."""


OperationVerifier = Callable[[Operation], None]
OperationVerifierLoader = Callable[[], None]

_OPERATION_VERIFIERS: dict[str, OperationVerifier] = {}
_OPERATION_VERIFIER_LOADERS: dict[str, OperationVerifierLoader] = {}
_LOADED_VERIFIER_PREFIXES: set[str] = set()


def register_operation_verifier(name_prefix: str, verifier: OperationVerifier) -> None:
    if not name_prefix:
        raise ValueError("operation verifier prefix must be non-empty")
    _OPERATION_VERIFIERS[name_prefix] = verifier


def register_operation_verifier_loader(
    name_prefix: str,
    loader: OperationVerifierLoader,
) -> None:
    if not name_prefix:
        raise ValueError("operation verifier loader prefix must be non-empty")
    _OPERATION_VERIFIER_LOADERS[name_prefix] = loader


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
    if _run_registered_dialect_verifier(op):
        return
    _load_dialect_verifier(op.name)
    _run_registered_dialect_verifier(op)


def _run_registered_dialect_verifier(op: Operation) -> bool:
    matched = False
    for name_prefix, verifier in tuple(_OPERATION_VERIFIERS.items()):
        if not op.name.startswith(name_prefix):
            continue
        matched = True
        try:
            verifier(op)
        except (TypeError, ValueError) as exc:
            raise VerificationError(f"{op.name}: {exc}") from exc
    return matched


def _load_dialect_verifier(op_name: str) -> None:
    for name_prefix, loader in tuple(_OPERATION_VERIFIER_LOADERS.items()):
        if name_prefix in _LOADED_VERIFIER_PREFIXES or not op_name.startswith(name_prefix):
            continue
        loader()
        _LOADED_VERIFIER_PREFIXES.add(name_prefix)


from intellic.dialects import verification as _dialect_verification  # noqa: F401,E402
