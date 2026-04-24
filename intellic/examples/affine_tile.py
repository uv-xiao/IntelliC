from __future__ import annotations

from dataclasses import dataclass

from intellic.ir.dialects import affine, builtin
from intellic.ir.dialects.memref import MemRefType
from intellic.ir.dialects.vector import VectorType
from intellic.ir.syntax import Block, Builder, Operation, Region, Type, index


@dataclass(frozen=True)
class AffineTiledAccessExample:
    module: Operation
    scalar_load: Operation
    scalar_store: Operation
    vector_load: Operation
    vector_store: Operation


def build_affine_tiled_access() -> AffineTiledAccessExample:
    f32 = Type("f32")
    memref_type = MemRefType(element_type=f32, shape=(None, None))
    vector_type = VectorType(element_type=f32, shape=(4,))
    block = Block(arg_types=(memref_type, index, index, index))
    memref, row, column, tile = block.arguments
    module = builtin.module(Region.from_block_list([block]))
    tiled_map = affine.AffineMap(dim_count=2, symbol_count=1, results=("d0 + s0", "d1"))
    tile_bound_map = affine.AffineMap(dim_count=2, symbol_count=1, results=("d0 + s0",))

    with Builder().insert_at_end(block) as builder:
        builder.insert(affine.min(tile_bound_map, dims=(row, column), symbols=(tile,)))
        builder.insert(affine.max(tile_bound_map, dims=(row, column), symbols=(tile,)))
        scalar_load = builder.insert(affine.load(memref, tiled_map, dims=(row, column), symbols=(tile,)))
        scalar_store = builder.insert(
            affine.store(scalar_load.results[0], memref, tiled_map, dims=(row, column), symbols=(tile,))
        )
        vector_load = builder.insert(
            affine.vector_load(memref, tiled_map, dims=(row, column), symbols=(tile,), vector_type=vector_type)
        )
        vector_store = builder.insert(
            affine.vector_store(vector_load.results[0], memref, tiled_map, dims=(row, column), symbols=(tile,))
        )

    return AffineTiledAccessExample(module, scalar_load, scalar_store, vector_load, vector_store)
