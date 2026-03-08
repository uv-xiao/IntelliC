from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


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


def register_intrinsic(decl: IntrinsicDecl) -> None:
    _INTRINSICS[decl.name] = decl


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


def simulate_intrinsic(
    intrinsic: str,
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object] | None,
    mode: str,
    trace: object | None = None,
    target: str = "generic",
) -> object:
    handler = resolve_handler(target, intrinsic, role="simulate")
    if handler is None:
        require_handler(target, intrinsic, role="simulate")
        raise AssertionError("unreachable")
    return handler(args=args, attrs=dict(attrs or {}), mode=mode, trace=trace)


def get_stub_diagnostic_code(intrinsic: str) -> str:
    return get_intrinsic_decl(intrinsic).stub_diagnostic


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
        IntrinsicDecl(
            "portable.reduction_sum", 1, "portable", "reduction_sum", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
        IntrinsicDecl(
            "portable.async_copy",
            1,
            "portable",
            "async_copy",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            produces_effects=("async_copy",),
        ),
        IntrinsicDecl("portable.barrier", 1, "portable", "barrier", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl(
            "portable.await",
            1,
            "portable",
            "await",
            "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC",
            requires_effects=("async_copy",),
            discharges_effects=("async_copy",),
        ),
        IntrinsicDecl("portable.mma", 1, "portable", "mma", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl(
            "portable.channel_send", 1, "portable", "channel_send", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
        IntrinsicDecl(
            "portable.channel_recv", 1, "portable", "channel_recv", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
        IntrinsicDecl(
            "portable.allreduce", 1, "portable", "allreduce", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"
        ),
    )
    for decl in declarations:
        register_intrinsic(decl)

    register_handlers(
        "generic",
        "portable.elementwise_binary",
        simulate=_simulate_elementwise_binary,
    )
    for intrinsic in (
        "portable.load",
        "portable.store",
        "portable.cast",
        "portable.broadcast",
        "portable.transpose",
        "portable.view",
        "portable.reshape",
        "portable.reduction_sum",
        "portable.async_copy",
        "portable.barrier",
        "portable.await",
        "portable.channel_send",
        "portable.channel_recv",
        "portable.allreduce",
    ):
        register_handlers("generic", intrinsic, simulate=_stub_simulate)
    register_handlers(
        "nvgpu",
        "portable.elementwise_binary",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_elementwise_binary,
    )
    register_handlers(
        "nvgpu",
        "portable.matmul",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_matmul_placeholder,
    )
    register_handlers(
        "pto",
        "portable.elementwise_binary",
        lower=_lower_passthrough,
        emit=_emit_passthrough,
        simulate=_simulate_elementwise_binary,
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
    lhs, rhs = args
    if operator == "add":
        return lhs + rhs
    if operator == "mul":
        return lhs * rhs
    raise ValueError(f"Unsupported simulated operator {operator!r}.")


def _simulate_matmul_placeholder(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del args, attrs, mode, trace
    return "matmul-sim"


def _stub_simulate(
    *, args: tuple[object, ...], attrs: Mapping[str, object], mode: str, trace: object | None = None
) -> object:
    del args, attrs, mode, trace
    raise NotImplementedError("stub intrinsic simulation should be handled by runtime fallback")


_bootstrap()


__all__ = [
    "HandlerDecl",
    "IntrinsicDecl",
    "get_intrinsic_decl",
    "get_stub_diagnostic_code",
    "has_handler",
    "lower_intrinsic",
    "register_handlers",
    "register_intrinsic",
    "require_handler",
    "resolve_handler",
    "simulate_intrinsic",
]
