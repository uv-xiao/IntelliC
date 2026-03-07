from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OpSpec:
    name: str
    phase: str
    latency: int
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    channel_reads: tuple[str, ...] = ()
    channel_writes: tuple[str, ...] = ()
    barrier_after: bool = False


OP_SPECS = {
    "elementwise_binary": OpSpec(
        name="elementwise_binary",
        phase="compute",
        latency=1,
        reads=("lhs", "rhs"),
        writes=("out",),
    ),
    "matmul": OpSpec(
        name="matmul",
        phase="compute",
        latency=2,
        reads=("lhs", "rhs"),
        writes=("out",),
    ),
    "load": OpSpec(name="load", phase="producer", latency=1, reads=("source",), writes=("out",)),
    "load_tile": OpSpec(name="load_tile", phase="producer", latency=1, reads=("source",), writes=("out",)),
    "store": OpSpec(name="store", phase="consumer", latency=1, reads=("value",), writes=("target",)),
    "store_tile": OpSpec(name="store_tile", phase="consumer", latency=1, reads=("value",), writes=("target",)),
    "async_copy": OpSpec(
        name="async_copy",
        phase="producer",
        latency=1,
        reads=("source",),
        writes=("target",),
        barrier_after=True,
    ),
    "mma": OpSpec(
        name="mma",
        phase="compute",
        latency=2,
        reads=("lhs", "rhs"),
        writes=("out",),
        barrier_after=True,
    ),
    "channel_send": OpSpec(
        name="channel_send",
        phase="sync",
        latency=1,
        reads=("value",),
        channel_writes=("channel",),
    ),
    "channel_recv": OpSpec(
        name="channel_recv",
        phase="sync",
        latency=1,
        writes=("out",),
        channel_reads=("channel",),
    ),
    "barrier": OpSpec(name="barrier", phase="sync", latency=1),
    "await": OpSpec(name="await", phase="sync", latency=1),
}


def get_op_spec(op_name: str) -> OpSpec:
    return OP_SPECS.get(op_name, OpSpec(name=op_name, phase="compute", latency=1))


def op_effects(op_name: str, op: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    spec = get_op_spec(op_name)
    effects = {
        "reads": tuple(str(op[field]) for field in spec.reads if field in op),
        "writes": tuple(str(op[field]) for field in spec.writes if field in op),
    }
    if spec.channel_reads or spec.channel_writes:
        effects["channel_reads"] = tuple(str(op[field]) for field in spec.channel_reads if field in op)
        effects["channel_writes"] = tuple(str(op[field]) for field in spec.channel_writes if field in op)
    return effects


__all__ = ["OP_SPECS", "OpSpec", "get_op_spec", "op_effects"]
