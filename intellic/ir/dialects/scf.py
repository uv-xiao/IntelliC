from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from intellic.ir.syntax import (
    Block,
    Builder,
    Operation,
    Region,
    Type,
    Value,
    i1,
    index,
)


@contextmanager
def body_builder(region: Region) -> Iterator[Builder]:
    if not region.blocks:
        raise ValueError("SCF body region must contain a block")
    builder = Builder()
    with builder.insert_at_end(region.blocks[0]) as active:
        yield active


def yield_(*operands: Value) -> Operation:
    return Operation.create("scf.yield", operands=tuple(operands))


def condition(condition_value: Value, *payload: Value) -> Operation:
    if condition_value.type != i1:
        raise TypeError("scf.condition condition must be i1 typed")
    return Operation.create("scf.condition", operands=(condition_value,) + tuple(payload))


def reduce_return(value: Value) -> Operation:
    return Operation.create("scf.reduce.return", operands=(value,))


@dataclass(frozen=True)
class ForallYield:
    """First-slice representation of a shared-output parallel yielding op."""

    value: Value
    region: Region


def forall_yield(value: Value, *, region: Region) -> ForallYield:
    _verify_forall_yield_region(region, value.type, "scf.forall.yield region")
    return ForallYield(value=value, region=region)


def forall_in_parallel(*yielding_ops: ForallYield) -> Operation:
    for yielding_op in yielding_ops:
        if not isinstance(yielding_op, ForallYield):
            raise TypeError("scf.forall.in_parallel requires forall yielding operations")
    return Operation.create(
        "scf.forall.in_parallel",
        operands=tuple(yielding_op.value for yielding_op in yielding_ops),
        properties={"yield_count": len(yielding_ops)},
        regions=tuple(yielding_op.region for yielding_op in yielding_ops),
    )


def if_(
    condition_value: Value,
    *,
    then_region: Region,
    else_region: Region | None = None,
    result_types: tuple[Type, ...] = (),
) -> Operation:
    if condition_value.type != i1:
        raise TypeError("scf.if condition must be i1 typed")
    if result_types and else_region is None:
        raise ValueError("scf.if result types require an else region")
    _verify_yielding_region(then_region, result_types, "scf.if then region")
    regions = [then_region]
    if else_region is not None:
        _verify_yielding_region(else_region, result_types, "scf.if else region")
        regions.append(else_region)
    return Operation.create(
        "scf.if",
        operands=(condition_value,),
        result_types=result_types,
        regions=tuple(regions),
    )


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
        body = Region.from_block_list(
            [Block(arg_types=(index,) + tuple(arg.type for arg in iter_args))]
        )
    _verify_loop_body(body, iter_args)
    return Operation.create(
        "scf.for",
        operands=(lower_bound, upper_bound, step) + tuple(iter_args),
        result_types=tuple(arg.type for arg in iter_args),
        properties={"iter_arg_count": len(iter_args)},
        regions=(body,),
    )


def while_(
    operands: tuple[Value, ...],
    *,
    before_region: Region,
    after_region: Region,
    result_types: tuple[Type, ...] | None = None,
) -> Operation:
    results = (
        result_types if result_types is not None else tuple(value.type for value in operands)
    )
    operand_types = tuple(value.type for value in operands)
    before_block = _single_block(before_region, "scf.while before region")
    after_block = _single_block(after_region, "scf.while after region")
    _verify_block_argument_types(before_block, operand_types, "scf.while before region")
    _verify_block_argument_types(after_block, results, "scf.while after region")
    before_terminator = _required_terminator(
        before_block,
        "scf.condition",
        "scf.while before region",
    )
    if not before_terminator.operands or before_terminator.operands[0].type != i1:
        raise TypeError("scf.condition first operand must be i1 typed")
    condition_payload = before_terminator.operands[1:]
    if len(condition_payload) != len(results):
        raise ValueError("scf.while condition payload count must match result types")
    _verify_value_types(condition_payload, results, "scf.while condition payload")
    _verify_yield_terminator(after_block, operand_types, "scf.while after region")
    return Operation.create(
        "scf.while",
        operands=operands,
        result_types=results,
        regions=(before_region, after_region),
    )


def execute_region(
    region: Region,
    *,
    result_types: tuple[Type, ...] = (),
    no_inline: bool = False,
) -> Operation:
    if not region.blocks:
        raise ValueError("scf.execute_region must own at least one block")
    for block in region.blocks:
        _verify_yield_terminator(block, result_types, "scf.execute_region region")
    return Operation.create(
        "scf.execute_region",
        result_types=result_types,
        properties={"no_inline": no_inline},
        regions=(region,),
    )


def index_switch(
    flag: Value,
    case_values: tuple[int, ...],
    case_regions: tuple[Region, ...],
    default_region: Region,
    *,
    result_types: tuple[Type, ...] = (),
) -> Operation:
    if flag.type != index:
        raise TypeError("scf.index_switch index flag must be index typed")
    if len(case_values) != len(case_regions):
        raise ValueError("scf.index_switch case values must match case regions")
    if len(set(case_values)) != len(case_values):
        raise ValueError("scf.index_switch case values must be unique")
    for value in case_values:
        if not isinstance(value, int):
            raise TypeError("scf.index_switch case values must be integers")
    for region in case_regions:
        _verify_yielding_region(region, result_types, "scf.index_switch case region")
    _verify_yielding_region(default_region, result_types, "scf.index_switch default region")
    return Operation.create(
        "scf.index_switch",
        operands=(flag,),
        result_types=result_types,
        properties={"case_values": case_values},
        regions=case_regions + (default_region,),
    )


def parallel(
    *,
    lower_bounds: tuple[Value, ...],
    upper_bounds: tuple[Value, ...],
    steps: tuple[Value, ...],
    init_vals: tuple[Value, ...] = (),
    body: Region,
) -> Operation:
    rank = _verify_index_triplets(lower_bounds, upper_bounds, steps, "scf.parallel")
    block = _single_block(body, "scf.parallel body")
    expected_arg_types = (index,) * rank
    _verify_block_argument_types(block, expected_arg_types, "scf.parallel body")
    result_types = tuple(value.type for value in init_vals)
    if init_vals:
        terminator = _required_terminator(block, "scf.reduce", "scf.parallel body")
        _verify_reduce_operation(terminator, result_types, "scf.parallel")
    elif block.operations and block.operations[-1].name == "scf.reduce":
        terminator = block.operations[-1]
        if terminator.operands:
            raise ValueError("scf.parallel no-result reduce terminator must not have operands")
        _verify_reduce_operation(terminator, (), "scf.parallel")
    elif block.operations and block.operations[-1].name == "scf.yield":
        _verify_yield_terminator(block, (), "scf.parallel body")
    return Operation.create(
        "scf.parallel",
        operands=lower_bounds + upper_bounds + steps + init_vals,
        result_types=result_types,
        properties={"rank": rank, "init_count": len(init_vals)},
        regions=(body,),
    )


def reduce(*operands: Value, regions: tuple[Region, ...]) -> Operation:
    op = Operation.create(
        "scf.reduce",
        operands=tuple(operands),
        properties={"operand_count": len(operands)},
        regions=regions,
    )
    _verify_reduce_operation(op, tuple(operand.type for operand in operands), "scf.reduce")
    return op


def forall(
    *,
    lower_bounds: tuple[Value, ...],
    upper_bounds: tuple[Value, ...],
    steps: tuple[Value, ...],
    shared_outputs: tuple[Value, ...] = (),
    body: Region,
    mapping: tuple[object, ...] = (),
) -> Operation:
    rank = _verify_index_triplets(lower_bounds, upper_bounds, steps, "scf.forall")
    if mapping and len(mapping) != rank:
        raise ValueError("scf.forall mapping attribute count must match rank")
    block = _single_block(body, "scf.forall body")
    shared_types = tuple(value.type for value in shared_outputs)
    expected_arg_types = ((index,) * rank) + shared_types
    _verify_block_argument_types(block, expected_arg_types, "scf.forall body")
    terminator = _required_terminator(block, "scf.forall.in_parallel", "scf.forall body")
    if len(terminator.operands) != len(shared_outputs):
        raise ValueError("scf.forall.in_parallel operand count must match shared outputs")
    if len(terminator.regions) != len(shared_outputs):
        raise ValueError("scf.forall.in_parallel yielding region count must match shared outputs")
    try:
        _verify_value_types(terminator.operands, shared_types, "scf.forall shared output")
    except TypeError as exc:
        raise TypeError("scf.forall shared output type mismatch") from exc
    for region, type_ in zip(terminator.regions, shared_types):
        _verify_forall_yield_region(region, type_, "scf.forall.in_parallel yielding region")
    return Operation.create(
        "scf.forall",
        operands=lower_bounds + upper_bounds + steps + shared_outputs,
        result_types=shared_types,
        properties={
            "rank": rank,
            "shared_output_count": len(shared_outputs),
            "mapping": mapping,
        },
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


def _single_block(region: Region, owner: str) -> Block:
    if len(region.blocks) != 1:
        raise ValueError(f"{owner} must be single-block")
    return region.blocks[0]


def _required_terminator(block: Block, name: str, owner: str) -> Operation:
    if not block.operations:
        raise ValueError(f"{owner} must terminate with {name}")
    terminator = block.operations[-1]
    if terminator.name != name:
        raise ValueError(f"{owner} must terminate with {name}")
    return terminator


def _verify_yielding_region(region: Region, result_types: tuple[Type, ...], owner: str) -> None:
    block = _single_block(region, owner)
    _verify_yield_terminator(block, result_types, owner)


def _verify_yield_terminator(block: Block, result_types: tuple[Type, ...], owner: str) -> None:
    terminator = _required_terminator(block, "scf.yield", owner)
    if len(terminator.operands) != len(result_types):
        raise ValueError(f"{owner} yield count must match result types")
    try:
        _verify_value_types(terminator.operands, result_types, owner)
    except TypeError as exc:
        raise TypeError(f"{owner} yield type mismatch") from exc


def _verify_reduce_operation(op: Operation, result_types: tuple[Type, ...], owner: str) -> None:
    if len(op.operands) != len(result_types):
        raise ValueError(f"{owner} reduction count must match result types")
    if len(op.regions) != len(op.operands):
        raise ValueError(f"{owner} reduction region count must match reduction operands")
    _verify_value_types(op.operands, result_types, f"{owner} reduction")
    for operand, region in zip(op.operands, op.regions):
        block = _single_block(region, "scf.reduce region")
        _verify_block_argument_types(block, (operand.type, operand.type), "scf.reduce region")
        terminator = _required_terminator(block, "scf.reduce.return", "scf.reduce region")
        if len(terminator.operands) != 1:
            raise ValueError("scf.reduce.return must have one operand")
        if terminator.operands[0].type != operand.type:
            raise TypeError("scf.reduce.return operand type must match reduce operand")


def _verify_forall_yield_region(region: Region, type_: Type, owner: str) -> None:
    block = _single_block(region, owner)
    _verify_block_argument_types(block, (type_,), owner)
    _verify_yield_terminator(block, (type_,), owner)


def _verify_block_argument_types(block: Block, types: tuple[Type, ...], owner: str) -> None:
    if len(block.arguments) != len(types):
        raise ValueError(f"{owner} argument count does not match expected types")
    for index_, (argument, type_) in enumerate(zip(block.arguments, types)):
        if argument.type != type_:
            raise TypeError(f"{owner} argument {index_} type mismatch")


def _verify_value_types(values: tuple[Value, ...], types: tuple[Type, ...], owner: str) -> None:
    for index_, (value, type_) in enumerate(zip(values, types)):
        if value.type != type_:
            raise TypeError(f"{owner} value {index_} type mismatch")


def _verify_index_triplets(
    lower_bounds: tuple[Value, ...],
    upper_bounds: tuple[Value, ...],
    steps: tuple[Value, ...],
    owner: str,
) -> int:
    if not lower_bounds:
        raise ValueError(f"{owner} must have at least one dimension")
    if len(lower_bounds) != len(upper_bounds) or len(lower_bounds) != len(steps):
        raise ValueError(f"{owner} bounds and steps must have equal rank")
    for value in lower_bounds + upper_bounds + steps:
        if value.type != index:
            raise TypeError(f"{owner} bounds and steps must be index typed")
    return len(lower_bounds)
