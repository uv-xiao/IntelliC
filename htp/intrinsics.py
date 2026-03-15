from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any

from htp.runtime.errors import raise_stub


@dataclass(frozen=True)
class IntrinsicDecl:
    name: str
    version: int
    portability: str
    op_name: str
    stub_diagnostic: str
    requires_effects: tuple[str, ...] = ()
    produces_effects: tuple[str, ...] = ()
    discharges_effects: tuple[str, ...] = ()


@dataclass(frozen=True)
class HandlerDecl:
    lower: Callable[..., object] | None = None
    emit: Callable[..., object] | None = None
    simulate: Callable[..., object] | None = None

    def has(self, role: str) -> bool:
        return getattr(self, role) is not None


_INTRINSICS: dict[str, IntrinsicDecl] = {}
_HANDLERS: dict[tuple[str, str], HandlerDecl] = {}
_PACKAGES: dict[str, tuple[str, ...]] = {}


def register_intrinsic(decl: IntrinsicDecl) -> None:
    _INTRINSICS[decl.name] = decl


def register_intrinsic_package(
    package_id: str, decls: tuple[IntrinsicDecl, ...] | list[IntrinsicDecl]
) -> None:
    decl_tuple = tuple(decls)
    for decl in decl_tuple:
        register_intrinsic(decl)
    _PACKAGES[package_id] = tuple(decl.name for decl in decl_tuple)


def register_handlers(
    target: str,
    intrinsic: str,
    *,
    lower: Callable[..., object] | bool = False,
    emit: Callable[..., object] | bool = False,
    simulate: Callable[..., object] | bool = False,
) -> None:
    _HANDLERS[(target, intrinsic)] = HandlerDecl(
        lower=_normalize_handler(lower),
        emit=_normalize_handler(emit),
        simulate=_normalize_handler(simulate),
    )


def get_intrinsic_decl(name: str) -> IntrinsicDecl:
    if name not in _INTRINSICS:
        raise KeyError(f"Unknown intrinsic {name!r}")
    return _INTRINSICS[name]


def resolve_handler(target: str, intrinsic: str, *, role: str) -> Callable[..., object] | None:
    handler = _HANDLERS.get((target, intrinsic))
    if handler is not None and handler.has(role):
        return getattr(handler, role)
    fallback = _HANDLERS.get(("generic", intrinsic))
    if fallback is not None and fallback.has(role):
        return getattr(fallback, role)
    return None


def has_handler(target: str, intrinsic: str, *, role: str) -> bool:
    return resolve_handler(target, intrinsic, role=role) is not None


def require_handler(target: str, intrinsic: str, *, role: str) -> None:
    if not has_handler(target, intrinsic, role=role):
        raise ValueError(
            f"HTP.INTRINSIC.MISSING_HANDLER: target {target!r} has no {role!r} handler for {intrinsic!r}."
        )


def lower_intrinsic(target: str, op: Mapping[str, Any]) -> dict[str, Any]:
    intrinsic = str(op.get("intrinsic", ""))
    handler = resolve_handler(target, intrinsic, role="lower")
    if handler is None:
        require_handler(target, intrinsic, role="lower")
        raise AssertionError("unreachable")
    lowered = handler(op=dict(op), target=target)
    if not isinstance(lowered, Mapping):
        raise TypeError(f"Intrinsic lower handler for {intrinsic!r} must return a mapping.")
    return dict(lowered)


def emit_intrinsic(target: str, op: Mapping[str, Any]) -> dict[str, Any]:
    intrinsic = str(op.get("intrinsic", ""))
    handler = resolve_handler(target, intrinsic, role="emit")
    if handler is None:
        require_handler(target, intrinsic, role="emit")
        raise AssertionError("unreachable")
    emitted = handler(op=dict(op), target=target)
    if not isinstance(emitted, Mapping):
        raise TypeError(f"Intrinsic emit handler for {intrinsic!r} must return a mapping.")
    return dict(emitted)


def simulate_intrinsic(
    intrinsic: str,
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object] | None,
    mode: str,
    trace: object | None = None,
    target: str = "generic",
    runtime: object | None = None,
) -> object:
    handler = resolve_handler(target, intrinsic, role="simulate")
    if handler is None:
        require_handler(target, intrinsic, role="simulate")
        raise AssertionError("unreachable")
    handler_kwargs = {
        "args": args,
        "attrs": dict(attrs or {}),
        "mode": mode,
        "trace": trace,
    }
    if _accepts_keyword(handler, "runtime"):
        handler_kwargs["runtime"] = runtime
    return handler(**handler_kwargs)


def get_stub_diagnostic_code(intrinsic: str) -> str:
    return get_intrinsic_decl(intrinsic).stub_diagnostic


def portable_intrinsics() -> tuple[IntrinsicDecl, ...]:
    return tuple(
        sorted(
            (decl for decl in _INTRINSICS.values() if decl.portability == "portable"),
            key=lambda item: item.name,
        )
    )


def backend_intrinsics() -> tuple[IntrinsicDecl, ...]:
    return tuple(
        sorted(
            (decl for decl in _INTRINSICS.values() if decl.portability != "portable"),
            key=lambda item: item.name,
        )
    )


def registered_intrinsic_packages() -> dict[str, tuple[str, ...]]:
    return dict(_PACKAGES)


def _normalize_handler(value: Callable[..., object] | bool) -> Callable[..., object] | None:
    if callable(value):
        return value
    if value:
        return lambda **kwargs: kwargs
    return None


def _bootstrap() -> None:
    declarations = (
        IntrinsicDecl(
            "portable.elementwise_binary",
            1,
            "portable",
            "elementwise_binary",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
        ),
        IntrinsicDecl(
            "portable.elementwise_unary",
            1,
            "portable",
            "elementwise_unary",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
        ),
        IntrinsicDecl("portable.matmul", 1, "portable", "matmul", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.load", 1, "portable", "load", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.store", 1, "portable", "store", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.cast", 1, "portable", "cast", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl(
            "portable.broadcast", 1, "portable", "broadcast", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
        IntrinsicDecl(
            "portable.transpose", 1, "portable", "transpose", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
        IntrinsicDecl("portable.view", 1, "portable", "view", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.reshape", 1, "portable", "reshape", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.slice", 1, "portable", "slice", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.concat", 1, "portable", "concat", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl(
            "portable.relayout", 1, "portable", "relayout", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
        IntrinsicDecl(
            "portable.reduction_sum", 1, "portable", "reduction_sum", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
        IntrinsicDecl(
            "portable.async_copy",
            1,
            "portable",
            "async_copy",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            produces_effects=("token.async_copy", "memory.pending_copy"),
        ),
        IntrinsicDecl(
            "portable.barrier",
            1,
            "portable",
            "barrier",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("sync.barrier",),
            discharges_effects=("memory.pending_copy", "sync.barrier"),
        ),
        IntrinsicDecl(
            "portable.await",
            1,
            "portable",
            "await",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("token.async_copy",),
            discharges_effects=("token.async_copy", "memory.pending_copy"),
        ),
        IntrinsicDecl("portable.mma", 1, "portable", "mma", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl(
            "portable.channel_send",
            1,
            "portable",
            "channel_send",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("protocol.free_slot",),
            produces_effects=("protocol.used_slot",),
            discharges_effects=("protocol.free_slot",),
        ),
        IntrinsicDecl(
            "portable.channel_recv",
            1,
            "portable",
            "channel_recv",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("protocol.used_slot",),
            produces_effects=("protocol.free_slot",),
            discharges_effects=("protocol.used_slot",),
        ),
        IntrinsicDecl(
            "portable.allreduce",
            1,
            "portable",
            "allreduce",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("collective.pending_allreduce",),
            produces_effects=("collective.allreduce",),
            discharges_effects=("collective.pending_allreduce", "collective.allreduce"),
        ),
        IntrinsicDecl(
            "portable.allgather",
            1,
            "portable",
            "allgather",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("collective.pending_allgather",),
            produces_effects=("collective.allgather",),
            discharges_effects=("collective.pending_allgather", "collective.allgather"),
        ),
        IntrinsicDecl(
            "portable.reduce_scatter",
            1,
            "portable",
            "reduce_scatter",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("collective.pending_reduce_scatter",),
            produces_effects=("collective.reduce_scatter",),
            discharges_effects=("collective.pending_reduce_scatter", "collective.reduce_scatter"),
        ),
        IntrinsicDecl("nvgpu.cp_async", 1, "backend", "cp_async", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("nvgpu.ldmatrix", 1, "backend", "ldmatrix", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("nvgpu.mma_sync", 1, "backend", "mma_sync", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("nvgpu.wgmma", 1, "backend", "wgmma", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("nvgpu.tma_load", 1, "backend", "tma_load", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("nvgpu.tma_store", 1, "backend", "tma_store", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("nvgpu.commit", 1, "backend", "commit", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
    )
    register_intrinsic_package("htp.core.portable", declarations)

    register_handlers(
        "generic",
        "portable.elementwise_binary",
        simulate=_simulate_elementwise_binary,
    )
    register_handlers(
        "generic",
        "portable.elementwise_unary",
        simulate=_simulate_elementwise_unary,
    )
    register_handlers(
        "generic",
        "portable.matmul",
        simulate=_simulate_matmul,
    )
    for intrinsic in (
        "portable.load",
        "portable.store",
        "portable.cast",
        "portable.broadcast",
        "portable.transpose",
        "portable.view",
        "portable.reshape",
        "portable.slice",
        "portable.concat",
        "portable.relayout",
        "portable.reduction_sum",
        "portable.async_copy",
        "portable.barrier",
        "portable.await",
        "portable.channel_send",
        "portable.channel_recv",
        "portable.allreduce",
        "portable.allgather",
        "portable.reduce_scatter",
    ):
        register_handlers("generic", intrinsic, simulate=_portable_simulator_for(intrinsic))
    register_handlers(
        "nvgpu",
        "portable.elementwise_binary",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_elementwise_binary,
    )
    register_handlers(
        "nvgpu",
        "portable.elementwise_unary",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_elementwise_unary,
    )
    register_handlers(
        "nvgpu",
        "portable.matmul",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_matmul,
    )
    for intrinsic in (
        "portable.async_copy",
        "portable.barrier",
        "portable.await",
        "portable.reduction_sum",
        "portable.broadcast",
        "portable.slice",
        "portable.concat",
        "portable.channel_send",
        "portable.channel_recv",
        "portable.mma",
        "portable.allreduce",
        "portable.allgather",
        "portable.reduce_scatter",
    ):
        register_handlers(
            "nvgpu",
            intrinsic,
            lower=_lower_passthrough,
            emit=_emit_passthrough,
            simulate=_portable_simulator_for(intrinsic),
        )
    for intrinsic in (
        "nvgpu.cp_async",
        "nvgpu.ldmatrix",
        "nvgpu.mma_sync",
        "nvgpu.wgmma",
        "nvgpu.tma_load",
        "nvgpu.tma_store",
        "nvgpu.commit",
    ):
        register_handlers(
            "nvgpu",
            intrinsic,
            lower=_lower_passthrough,
            emit=_emit_passthrough,
            simulate=_nvgpu_simulator_for(intrinsic),
        )
    register_handlers(
        "pto",
        "portable.elementwise_binary",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_elementwise_binary,
    )
    register_handlers(
        "pto",
        "portable.elementwise_unary",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_elementwise_unary,
    )
    register_handlers(
        "pto",
        "portable.matmul",
        simulate=_simulate_matmul,
    )


def _lower_passthrough(*, op: Mapping[str, Any], target: str) -> dict[str, Any]:
    payload = dict(op)
    payload.setdefault("target", target)
    return payload


def _emit_passthrough(*, op: Mapping[str, Any], target: str) -> dict[str, Any]:
    return {"target": target, "intrinsic": op.get("intrinsic")}


def _simulate_elementwise_binary(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    operator = str(attrs.get("operator", "add"))
    lhs = args[0] if args else attrs.get("lhs_const")
    rhs = args[1] if len(args) > 1 else attrs.get("rhs_const")
    if lhs is None:
        lhs = attrs.get("lhs_const")
    if rhs is None:
        rhs = attrs.get("rhs_const")
    if lhs is None or rhs is None:
        raise ValueError("Simulated elementwise_binary requires two operands.")
    if operator == "add":
        return lhs + rhs
    if operator == "sub":
        return lhs - rhs
    if operator == "mul":
        return lhs * rhs
    if operator == "div":
        return lhs / rhs
    raise ValueError(f"Unsupported simulated operator {operator!r}.")


def _simulate_elementwise_unary(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    operator = str(attrs.get("operator", "identity"))
    (source,) = args
    if operator == "identity":
        return source
    if operator == "neg":
        return -source
    if operator == "recip":
        return 1.0 / source
    if operator == "sigmoid":
        import math

        return 1.0 / (1.0 + math.exp(-float(source)))
    if operator == "exp":
        import math

        return math.exp(float(source))
    raise ValueError(f"Unsupported simulated unary operator {operator!r}.")


def _simulate_matmul(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del attrs, mode, trace
    import numpy as np

    lhs, rhs = args[:2]
    return np.matmul(lhs, rhs)


def _simulate_load(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del attrs, mode, trace
    return args[0]


def _simulate_store(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del attrs, mode, trace
    target, value = args[:2]
    try:
        target[...] = value
    except Exception:
        return value
    return target


def _simulate_cast(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    source = args[0]
    dtype = str(attrs.get("dtype", ""))
    if hasattr(source, "astype") and dtype:
        return source.astype(dtype)
    return source


def _simulate_broadcast(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    import numpy as np

    return np.broadcast_to(args[0], tuple(attrs.get("shape", ())))


def _simulate_transpose(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    import numpy as np

    return np.transpose(args[0], axes=tuple(attrs.get("axes", ())))


def _simulate_view_like(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    source = args[0]
    shape = tuple(attrs.get("shape", ()))
    if not shape:
        return source
    if hasattr(source, "reshape"):
        return source.reshape(shape)
    return source


def _simulate_slice(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    source = args[0]
    offsets = tuple(
        _coerce_slice_index(item, axis=index, source=source, kind="offset")
        for index, item in enumerate(attrs.get("offsets", ()))
    )
    sizes = tuple(
        _coerce_slice_index(item, axis=index, source=source, kind="size", offset=offsets[index])
        for index, item in enumerate(attrs.get("sizes", ()))
    )
    slices = tuple(slice(offset, offset + size) for offset, size in zip(offsets, sizes))
    return source[slices]


def _coerce_slice_index(
    item: object,
    *,
    axis: int,
    source: object,
    kind: str,
    offset: int = 0,
) -> int:
    try:
        return int(item)
    except (TypeError, ValueError):
        pass
    if kind == "size" and hasattr(source, "shape"):
        return int(source.shape[axis]) - offset
    raise ValueError(f"Slice {kind} {item!r} is not concretely replayable in sim mode.")


def _simulate_concat(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    import numpy as np

    return np.concatenate(args, axis=int(attrs.get("axis", 0) or 0))


def _simulate_reduction_sum(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del mode, trace
    import numpy as np

    axis = attrs.get("axis")
    return np.sum(args[0], axis=axis)


def _simulate_async_copy(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del attrs, mode, trace, runtime
    import numpy as np

    return np.array(args[0], copy=True)


def _simulate_barrier(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del args, attrs, mode, trace, runtime
    return None


def _simulate_await(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del attrs, mode, trace, runtime
    return args[0]


def _simulate_mma(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del attrs, mode, trace
    import numpy as np

    lhs, rhs = args[:2]
    accum = args[2] if len(args) > 2 else 0
    return np.matmul(lhs, rhs) + accum


def _simulate_channel_send(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del mode, trace
    channel = str(attrs.get("channel", "default"))
    if runtime is None:
        raise_stub(
            "HTP.REPLAY.STUB_HIT",
            node_id=f"intrinsic::portable.channel_send::{channel}",
            entity_id=channel,
            kind="intrinsic",
            detail="channel send needs a runtime to hold replay queue state",
        )
    queues = getattr(runtime, "channel_queues", None)
    if queues is None:
        queues = {}
        setattr(runtime, "channel_queues", queues)
    queues.setdefault(channel, []).append(args[0] if args else None)
    return args[0] if args else None


def _simulate_channel_recv(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del args, mode, trace
    channel = str(attrs.get("channel", "default"))
    if runtime is None:
        raise_stub(
            "HTP.REPLAY.STUB_HIT",
            node_id=f"intrinsic::portable.channel_recv::{channel}",
            entity_id=channel,
            kind="intrinsic",
            detail="channel recv needs a runtime to hold replay queue state",
        )
    queues = getattr(runtime, "channel_queues", None)
    if not isinstance(queues, dict) or not queues.get(channel):
        raise_stub(
            "HTP.REPLAY.STUB_HIT",
            node_id=f"intrinsic::portable.channel_recv::{channel}",
            entity_id=channel,
            kind="intrinsic",
            detail=f"channel '{channel}' is empty in sim replay",
        )
    return queues[channel].pop(0)


def _simulate_allreduce(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del attrs, mode, trace, runtime
    return args[0]


def _simulate_allgather(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del attrs, mode, trace, runtime
    return args[0]


def _simulate_reduce_scatter(
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: object | None = None,
) -> object:
    del attrs, mode, trace, runtime
    return args[0]


def _simulate_nvgpu_identity(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del attrs, mode, trace
    return args[0] if args else None


def _portable_simulator_for(intrinsic: str) -> Callable[..., object]:
    mapping = {
        "portable.load": _simulate_load,
        "portable.store": _simulate_store,
        "portable.cast": _simulate_cast,
        "portable.broadcast": _simulate_broadcast,
        "portable.transpose": _simulate_transpose,
        "portable.view": _simulate_view_like,
        "portable.reshape": _simulate_view_like,
        "portable.slice": _simulate_slice,
        "portable.concat": _simulate_concat,
        "portable.relayout": _simulate_view_like,
        "portable.reduction_sum": _simulate_reduction_sum,
        "portable.async_copy": _simulate_async_copy,
        "portable.barrier": _simulate_barrier,
        "portable.await": _simulate_await,
        "portable.channel_send": _simulate_channel_send,
        "portable.channel_recv": _simulate_channel_recv,
        "portable.allreduce": _simulate_allreduce,
        "portable.allgather": _simulate_allgather,
        "portable.reduce_scatter": _simulate_reduce_scatter,
        "portable.mma": _simulate_mma,
    }
    return mapping[intrinsic]


def _nvgpu_simulator_for(intrinsic: str) -> Callable[..., object]:
    mapping = {
        "nvgpu.cp_async": _simulate_async_copy,
        "nvgpu.ldmatrix": _simulate_nvgpu_identity,
        "nvgpu.mma_sync": _simulate_mma,
        "nvgpu.wgmma": _simulate_mma,
        "nvgpu.tma_load": _simulate_async_copy,
        "nvgpu.tma_store": _simulate_store,
        "nvgpu.commit": _simulate_nvgpu_identity,
    }
    return mapping[intrinsic]


def _accepts_keyword(handler: Callable[..., object], name: str) -> bool:
    try:
        params = signature(handler).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(parameter.kind == Parameter.VAR_KEYWORD or parameter.name == name for parameter in params)


def _stub_simulate(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del args, attrs, mode, trace
    raise NotImplementedError("stub intrinsic simulation should be handled by runtime fallback")


_bootstrap()


__all__ = [
    "HandlerDecl",
    "IntrinsicDecl",
    "backend_intrinsics",
    "emit_intrinsic",
    "get_intrinsic_decl",
    "get_stub_diagnostic_code",
    "has_handler",
    "lower_intrinsic",
    "portable_intrinsics",
    "register_handlers",
    "register_intrinsic",
    "register_intrinsic_package",
    "registered_intrinsic_packages",
    "require_handler",
    "resolve_handler",
    "simulate_intrinsic",
]
