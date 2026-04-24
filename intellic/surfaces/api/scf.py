from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

from intellic.ir.dialects import scf as scf_dialect
from intellic.ir.syntax import Block, Region, Value, index
from intellic.surfaces.api import builders


@dataclass
class ForLoopBuilder:
    lower_bound: Value
    upper_bound: Value
    step: Value
    iter_args: tuple[Value, ...]
    body: Region
    arguments: tuple[Value, ...]
    results: tuple[Value, ...] = ()

    def __enter__(self) -> "ForLoopBuilder":
        self._cm = builders.nested_insertion(self.body.blocks[0])
        self._cm.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        self._cm.__exit__(exc_type, exc, tb)
        if exc_type is not None:
            return False
        op = builders.emit(
            scf_dialect.for_(
                self.lower_bound,
                self.upper_bound,
                self.step,
                iter_args=self.iter_args,
                body=self.body,
            ),
            "builder:scf.for",
        )
        self.results = op.results
        return False


def for_(lower_bound: Value, upper_bound: Value, step: Value, iter_args: tuple[Value, ...] = ()) -> ForLoopBuilder:
    body = Region.from_block_list([Block(arg_types=(index,) + tuple(arg.type for arg in iter_args))])
    return ForLoopBuilder(
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        step=step,
        iter_args=iter_args,
        body=body,
        arguments=body.blocks[0].arguments,
    )


def yield_(*operands: Value) -> None:
    builders.emit(scf_dialect.yield_(*operands), "builder:scf.yield")
