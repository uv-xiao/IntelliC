from __future__ import annotations

from dataclasses import dataclass

from intellic.dialects.memref import MemRefType
from intellic.dialects.vector import VectorType
from intellic.ir.syntax import Operation, Value, index


@dataclass(frozen=True)
class AffineMap:
    dim_count: int
    symbol_count: int
    results: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.dim_count < 0 or self.symbol_count < 0:
            raise ValueError("affine map counts must be non-negative")
        if not self.results:
            raise ValueError("affine map must have at least one result")


@dataclass(frozen=True)
class AffineSet:
    dim_count: int
    symbol_count: int
    constraints: tuple[str, ...]


def apply(map: AffineMap, dims: tuple[Value, ...], symbols: tuple[Value, ...]) -> Operation:
    _verify_affine_operands(map, dims, symbols)
    if len(map.results) != 1:
        raise ValueError("affine.apply requires a one-result map")
    return Operation.create(
        "affine.apply",
        operands=dims + symbols,
        result_types=(index,),
        properties={"map": map, "dim_count": len(dims), "symbol_count": len(symbols)},
    )


def load(memref: Value, map: AffineMap, dims: tuple[Value, ...], symbols: tuple[Value, ...]) -> Operation:
    memref_type = _require_memref(memref)
    _verify_memory_map(memref_type, map, dims, symbols)
    return Operation.create(
        "affine.load",
        operands=(memref,) + dims + symbols,
        result_types=(memref_type.element_type,),
        properties={"map": map, "dim_count": len(dims), "symbol_count": len(symbols)},
    )


def store(
    value: Value,
    memref: Value,
    map: AffineMap,
    dims: tuple[Value, ...],
    symbols: tuple[Value, ...],
) -> Operation:
    memref_type = _require_memref(memref)
    if value.type != memref_type.element_type:
        raise TypeError("affine.store value type must match memref element type")
    _verify_memory_map(memref_type, map, dims, symbols)
    return Operation.create(
        "affine.store",
        operands=(value, memref) + dims + symbols,
        properties={"map": map, "dim_count": len(dims), "symbol_count": len(symbols)},
    )


def vector_load(
    memref: Value,
    map: AffineMap,
    dims: tuple[Value, ...],
    symbols: tuple[Value, ...],
    vector_type: VectorType,
) -> Operation:
    memref_type = _require_memref(memref)
    if vector_type.element_type != memref_type.element_type:
        raise TypeError("affine.vector_load element type must match memref element type")
    _verify_memory_map(memref_type, map, dims, symbols)
    return Operation.create(
        "affine.vector_load",
        operands=(memref,) + dims + symbols,
        result_types=(vector_type,),
        properties={"map": map, "dim_count": len(dims), "symbol_count": len(symbols)},
    )


def vector_store(
    value: Value,
    memref: Value,
    map: AffineMap,
    dims: tuple[Value, ...],
    symbols: tuple[Value, ...],
) -> Operation:
    memref_type = _require_memref(memref)
    if not isinstance(value.type, VectorType):
        raise TypeError("affine.vector_store value must be a vector")
    if value.type.element_type != memref_type.element_type:
        raise TypeError("affine.vector_store element type must match memref element type")
    _verify_memory_map(memref_type, map, dims, symbols)
    return Operation.create(
        "affine.vector_store",
        operands=(value, memref) + dims + symbols,
        properties={"map": map, "dim_count": len(dims), "symbol_count": len(symbols)},
    )


def for_(lower_map: AffineMap, upper_map: AffineMap, step: int, operands: tuple[Value, ...], body) -> Operation:
    if step <= 0:
        raise ValueError("affine.for step must be positive")
    return Operation.create(
        "affine.for",
        operands=operands,
        properties={"lower_map": lower_map, "upper_map": upper_map, "step": step},
        regions=(body,),
    )


def if_(set: AffineSet, operands: tuple[Value, ...], then_region, else_region=None) -> Operation:
    regions = (then_region,) if else_region is None else (then_region, else_region)
    return Operation.create("affine.if", operands=operands, properties={"set": set}, regions=regions)


def min(map: AffineMap, dims: tuple[Value, ...], symbols: tuple[Value, ...]) -> Operation:
    _verify_affine_operands(map, dims, symbols)
    return Operation.create("affine.min", operands=dims + symbols, result_types=(index,), properties={"map": map})


def max(map: AffineMap, dims: tuple[Value, ...], symbols: tuple[Value, ...]) -> Operation:
    _verify_affine_operands(map, dims, symbols)
    return Operation.create("affine.max", operands=dims + symbols, result_types=(index,), properties={"map": map})


def _verify_affine_operands(map: AffineMap, dims: tuple[Value, ...], symbols: tuple[Value, ...]) -> None:
    if len(dims) != map.dim_count:
        raise ValueError("affine map dimension count does not match operands")
    if len(symbols) != map.symbol_count:
        raise ValueError("affine map symbol count does not match operands")
    for value in dims + symbols:
        if value.type != index:
            raise TypeError("affine map operands must be index typed")


def _verify_memory_map(memref_type: MemRefType, map: AffineMap, dims: tuple[Value, ...], symbols: tuple[Value, ...]) -> None:
    _verify_affine_operands(map, dims, symbols)
    if len(map.results) != memref_type.rank:
        raise ValueError("affine memory map result count must match memref rank")


def _require_memref(value: Value) -> MemRefType:
    if not isinstance(value.type, MemRefType):
        raise TypeError("affine memory operation requires a memref operand")
    return value.type
