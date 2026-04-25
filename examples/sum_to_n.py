from dataclasses import dataclass

from intellic.ir.syntax import Value, i32, index
from intellic.surfaces.api import arith, func, scf


@dataclass(frozen=True)
class SumToNExample:
    operation: object
    evidence: tuple[str, ...]
    zero_i: Value


def build_sum_to_n() -> SumToNExample:
    captures: dict[str, Value] = {}

    @func.ir_function
    def sum_to_n(n: index) -> i32:
        zero_i = arith.constant(0, index)
        one_i = arith.constant(1, index)
        zero = arith.constant(0, i32)
        captures["zero_i"] = zero_i

        with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
            i, total = loop.arguments
            total_next = arith.addi(total, arith.index_cast(i, i32))
            scf.yield_(total_next)

        return loop.results[0]

    return SumToNExample(sum_to_n.operation, sum_to_n.evidence, captures["zero_i"])
