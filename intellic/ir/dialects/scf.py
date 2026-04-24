from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from intellic.ir.syntax import Block, Builder, Operation, Region, Value, index


@contextmanager
def body_builder(region: Region) -> Iterator[Builder]:
    if not region.blocks:
        raise ValueError("SCF body region must contain a block")
    builder = Builder()
    with builder.insert_at_end(region.blocks[0]) as active:
        yield active


def yield_(*operands: Value) -> Operation:
    return Operation.create("scf.yield", operands=tuple(operands))


def for_(
    lower_bound: Value,
    upper_bound: Value,
    step: Value,
    iter_args: tuple[Value, ...] = (),
    body: Region | None = None,
) -> Operation:
    if lower_bound.type != index or upper_bound.type != index or step.type != index:
        raise TypeError("scf.for bounds and step must be index typed")
    if body is None:
        body = Region.from_block_list([Block(arg_types=(index,) + tuple(arg.type for arg in iter_args))])
    _verify_loop_body(body, iter_args)
    return Operation.create(
        "scf.for",
        operands=(lower_bound, upper_bound, step) + tuple(iter_args),
        result_types=tuple(arg.type for arg in iter_args),
        properties={"iter_arg_count": len(iter_args)},
        regions=(body,),
    )


def _verify_loop_body(body: Region, iter_args: tuple[Value, ...]) -> None:
    if len(body.blocks) != 1:
        raise ValueError("scf.for body must be single-block")
    block = body.blocks[0]
    expected_arg_count = 1 + len(iter_args)
    if len(block.arguments) != expected_arg_count:
        raise ValueError("scf.for body argument count does not match iter_args")
    if block.arguments[0].type != index:
        raise TypeError("scf.for induction argument must be index typed")
    for index_, value in enumerate(iter_args, start=1):
        if block.arguments[index_].type != value.type:
            raise TypeError("scf.for iter argument type mismatch")
    if not block.operations:
        raise ValueError("scf.for body must terminate with scf.yield")
    terminator = block.operations[-1]
    if terminator.name != "scf.yield":
        raise ValueError("scf.for body must terminate with scf.yield")
    if len(terminator.operands) != len(iter_args):
        raise ValueError("scf.for yield count does not match iter_args")
    for yielded, initial in zip(terminator.operands, iter_args):
        if yielded.type != initial.type:
            raise TypeError("scf.for yielded type does not match iter_arg")
