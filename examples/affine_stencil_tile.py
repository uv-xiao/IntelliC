from __future__ import annotations

from dataclasses import dataclass

from examples.common import ExampleRun, print_example_run
from intellic.actions import passes
from intellic.dialects import affine, arith as arith_dialect, builtin
from intellic.dialects.memref import MemRefType
from intellic.dialects.vector import VectorType
from intellic.ir.actions import PipelineRun
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import Block, Builder, Region, i32, index, verify_operation
from intellic.ir.syntax.printer import print_operation


@dataclass(frozen=True)
class AffineStencilTileExample:
    module: object


def build_example() -> AffineStencilTileExample:
    memref_type = MemRefType(element_type=i32, shape=(None, None))
    vector_type = VectorType(element_type=i32, shape=(4,))
    block = Block(arg_types=(memref_type, index, index, index, index))
    memref, row, column, tile, width = block.arguments
    module = builtin.module(Region.from_block_list([block]))

    center_map = affine.AffineMap(dim_count=2, symbol_count=2, results=("d0", "d1"))
    west_map = affine.AffineMap(dim_count=2, symbol_count=2, results=("d0", "d1 - s0"))
    east_map = affine.AffineMap(dim_count=2, symbol_count=2, results=("d0", "d1 + s0"))
    clamp_map = affine.AffineMap(
        dim_count=2,
        symbol_count=2,
        results=("d0", "min(max(d1, s0), s1 - s0)"),
    )
    min_bound_map = affine.AffineMap(dim_count=2, symbol_count=2, results=("d0",))
    max_bound_map = affine.AffineMap(dim_count=2, symbol_count=2, results=("d1",))
    dims = (row, column)
    symbols = (tile, width)

    with Builder().insert_at_end(block) as builder:
        bounded_row = builder.insert(affine.min(min_bound_map, dims=dims, symbols=symbols))
        bounded_column = builder.insert(affine.max(max_bound_map, dims=dims, symbols=symbols))
        access_dims = (bounded_row.results[0], bounded_column.results[0])

        west = builder.insert(affine.load(memref, west_map, dims=access_dims, symbols=symbols))
        center = builder.insert(affine.load(memref, center_map, dims=access_dims, symbols=symbols))
        east = builder.insert(affine.load(memref, east_map, dims=access_dims, symbols=symbols))
        west_center = builder.insert(arith_dialect.addi(west.results[0], center.results[0]))
        stencil_sum = builder.insert(arith_dialect.addi(west_center.results[0], east.results[0]))

        builder.insert(
            affine.store(
                stencil_sum.results[0],
                memref,
                center_map,
                dims=access_dims,
                symbols=symbols,
            )
        )
        builder.insert(
            affine.store(
                center.results[0],
                memref,
                clamp_map,
                dims=access_dims,
                symbols=symbols,
            )
        )
        vector = builder.insert(
            affine.vector_load(
                memref,
                clamp_map,
                dims=access_dims,
                symbols=symbols,
                vector_type=vector_type,
            )
        )
        builder.insert(
            affine.vector_store(
                vector.results[0],
                memref,
                east_map,
                dims=access_dims,
                symbols=symbols,
            )
        )

    return AffineStencilTileExample(module=module)


def run_demo() -> ExampleRun:
    example = build_example()
    verify_operation(example.module)
    canonical_ir = print_operation(example.module)
    parse_print_idempotent = canonical_ir == print_operation(parse_operation(canonical_ir))

    run = PipelineRun(example.module)
    for action in (
        passes.verify_structure(),
        passes.common_subexpression_elimination(),
        passes.lower_affine_to_scf(),
    ):
        action.run(run)

    affine_accesses = run.db.query("AffineAccess")
    memory_effects = run.db.query("MemoryEffect")
    affine_expansions = run.db.query("AffineExpansion")
    cse_memory_effects = run.db.query("CSEMemoryEffect")

    return ExampleRun(
        name="affine_stencil_tile",
        canonical_ir=canonical_ir,
        parse_print_idempotent=parse_print_idempotent,
        action_names=tuple(record.value["name"] for record in run.db.query("ActionRun")),
        relation_counts={
            "UniqueAffineAccess": len({record.subject for record in affine_accesses}),
            "UniqueMemoryEffect": len({record.subject for record in memory_effects}),
            "ReadAccess": len(
                {record.subject for record in affine_accesses if record.value["kind"] == "read"}
            ),
            "WriteAccess": len(
                {record.subject for record in affine_accesses if record.value["kind"] == "write"}
            ),
            "CSEReadObserved": sum(
                1
                for record in cse_memory_effects
                if record.value["action"] == "read-observed"
            ),
            "CSESkipSideEffect": sum(
                1
                for record in cse_memory_effects
                if record.value["action"] == "skip-side-effect"
            ),
            "UniqueAffineExpansion": len({record.subject for record in affine_expansions}),
        },
        documented_gaps=("affine concrete memory execution is not implemented",),
    )


def main() -> None:
    print(print_example_run(run_demo()), end="")


if __name__ == "__main__":
    main()
