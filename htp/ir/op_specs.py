from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OpSpec:
    name: str
    intrinsic: str
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
        intrinsic="portable.elementwise_binary",
        phase="compute",
        latency=1,
        reads=("lhs", "rhs"),
        writes=("out",),
    ),
    "elementwise_unary": OpSpec(
        name="elementwise_unary",
        intrinsic="portable.elementwise_unary",
        phase="compute",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "matmul": OpSpec(
        name="matmul",
        intrinsic="portable.matmul",
        phase="compute",
        latency=2,
        reads=("lhs", "rhs"),
        writes=("out",),
    ),
    "load": OpSpec(
        name="load",
        intrinsic="portable.load",
        phase="producer",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "load_tile": OpSpec(
        name="load_tile",
        intrinsic="portable.load",
        phase="producer",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "store": OpSpec(
        name="store",
        intrinsic="portable.store",
        phase="consumer",
        latency=1,
        reads=("value",),
        writes=("target",),
    ),
    "store_tile": OpSpec(
        name="store_tile",
        intrinsic="portable.store",
        phase="consumer",
        latency=1,
        reads=("value",),
        writes=("target",),
    ),
    "cast": OpSpec(
        name="cast", intrinsic="portable.cast", phase="compute", latency=1, reads=("source",), writes=("out",)
    ),
    "broadcast": OpSpec(
        name="broadcast",
        intrinsic="portable.broadcast",
        phase="compute",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "transpose": OpSpec(
        name="transpose",
        intrinsic="portable.transpose",
        phase="compute",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "view": OpSpec(
        name="view", intrinsic="portable.view", phase="compute", latency=1, reads=("source",), writes=("out",)
    ),
    "reshape": OpSpec(
        name="reshape",
        intrinsic="portable.reshape",
        phase="compute",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "slice": OpSpec(
        name="slice",
        intrinsic="portable.slice",
        phase="compute",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "concat": OpSpec(
        name="concat",
        intrinsic="portable.concat",
        phase="compute",
        latency=1,
        writes=("out",),
    ),
    "relayout": OpSpec(
        name="relayout",
        intrinsic="portable.relayout",
        phase="compute",
        latency=1,
        reads=("source",),
        writes=("out",),
    ),
    "reduction_sum": OpSpec(
        name="reduction_sum",
        intrinsic="portable.reduction_sum",
        phase="compute",
        latency=2,
        reads=("source",),
        writes=("out",),
    ),
    "async_copy": OpSpec(
        name="async_copy",
        intrinsic="portable.async_copy",
        phase="producer",
        latency=1,
        reads=("source",),
        writes=("target",),
        barrier_after=True,
    ),
    "mma": OpSpec(
        name="mma",
        intrinsic="portable.mma",
        phase="compute",
        latency=2,
        reads=("lhs", "rhs"),
        writes=("out",),
        barrier_after=True,
    ),
    "cp_async": OpSpec(
        name="cp_async",
        intrinsic="nvgpu.cp_async",
        phase="producer",
        latency=1,
        reads=("source",),
        writes=("target",),
        barrier_after=True,
    ),
    "ldmatrix": OpSpec(
        name="ldmatrix",
        intrinsic="nvgpu.ldmatrix",
        phase="producer",
        latency=1,
        reads=("source",),
        writes=("target",),
    ),
    "mma_sync": OpSpec(
        name="mma_sync",
        intrinsic="nvgpu.mma_sync",
        phase="compute",
        latency=2,
        reads=("lhs", "rhs", "accum"),
        writes=("out",),
        barrier_after=True,
    ),
    "wgmma": OpSpec(
        name="wgmma",
        intrinsic="nvgpu.wgmma",
        phase="compute",
        latency=2,
        reads=("lhs", "rhs", "accum"),
        writes=("out",),
        barrier_after=True,
    ),
    "tma_load": OpSpec(
        name="tma_load",
        intrinsic="nvgpu.tma_load",
        phase="producer",
        latency=1,
        reads=("source",),
        writes=("target",),
        barrier_after=True,
    ),
    "tma_store": OpSpec(
        name="tma_store",
        intrinsic="nvgpu.tma_store",
        phase="consumer",
        latency=1,
        reads=("source",),
        writes=("target",),
        barrier_after=True,
    ),
    "commit": OpSpec(
        name="commit",
        intrinsic="nvgpu.commit",
        phase="consumer",
        latency=1,
        reads=("value",),
        writes=("target",),
    ),
    "channel_send": OpSpec(
        name="channel_send",
        intrinsic="portable.channel_send",
        phase="sync",
        latency=1,
        reads=("value",),
        channel_writes=("channel",),
    ),
    "channel_recv": OpSpec(
        name="channel_recv",
        intrinsic="portable.channel_recv",
        phase="sync",
        latency=1,
        writes=("out",),
        channel_reads=("channel",),
    ),
    "allreduce": OpSpec(
        name="allreduce",
        intrinsic="portable.allreduce",
        phase="sync",
        latency=2,
        reads=("source",),
        writes=("out",),
    ),
    "allgather": OpSpec(
        name="allgather",
        intrinsic="portable.allgather",
        phase="sync",
        latency=2,
        reads=("source",),
        writes=("out",),
    ),
    "reduce_scatter": OpSpec(
        name="reduce_scatter",
        intrinsic="portable.reduce_scatter",
        phase="sync",
        latency=2,
        reads=("source",),
        writes=("out",),
    ),
    "barrier": OpSpec(name="barrier", intrinsic="portable.barrier", phase="sync", latency=1),
    "await": OpSpec(name="await", intrinsic="portable.await", phase="sync", latency=1, reads=("token",)),
}


def get_op_spec(op_name: str) -> OpSpec:
    return OP_SPECS.get(
        op_name, OpSpec(name=op_name, intrinsic=f"portable.{op_name}", phase="compute", latency=1)
    )


def op_effects(op_name: str, op: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    spec = get_op_spec(op_name)
    if op_name == "concat":
        return {
            "reads": tuple(str(item) for item in op.get("inputs", ())),
            "writes": tuple(str(op[field]) for field in spec.writes if field in op),
        }
    effects = {
        "reads": tuple(str(op[field]) for field in spec.reads if field in op),
        "writes": tuple(str(op[field]) for field in spec.writes if field in op),
    }
    if spec.channel_reads or spec.channel_writes:
        effects["channel_reads"] = tuple(str(op[field]) for field in spec.channel_reads if field in op)
        effects["channel_writes"] = tuple(str(op[field]) for field in spec.channel_writes if field in op)
    return effects


__all__ = ["OP_SPECS", "OpSpec", "get_op_spec", "op_effects"]
