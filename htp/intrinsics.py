from __future__ import annotations

from dataclasses import dataclass


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
    lower: bool = False
    emit: bool = False
    simulate: bool = False


_INTRINSICS: dict[str, IntrinsicDecl] = {}
_HANDLERS: dict[tuple[str, str], HandlerDecl] = {}


def register_intrinsic(decl: IntrinsicDecl) -> None:
    _INTRINSICS[decl.name] = decl


def register_handlers(target: str, intrinsic: str, *, lower: bool = False, emit: bool = False, simulate: bool = False) -> None:
    _HANDLERS[(target, intrinsic)] = HandlerDecl(lower=lower, emit=emit, simulate=simulate)


def get_intrinsic_decl(name: str) -> IntrinsicDecl:
    if name not in _INTRINSICS:
        raise KeyError(f"Unknown intrinsic {name!r}")
    return _INTRINSICS[name]


def has_handler(target: str, intrinsic: str, *, role: str) -> bool:
    handler = _HANDLERS.get((target, intrinsic))
    if handler is None:
        return False
    return bool(getattr(handler, role))


def require_handler(target: str, intrinsic: str, *, role: str) -> None:
    if not has_handler(target, intrinsic, role=role):
        raise ValueError(
            f"HTP.INTRINSIC.MISSING_HANDLER: target {target!r} has no {role!r} handler for {intrinsic!r}."
        )


def get_stub_diagnostic_code(intrinsic: str) -> str:
    return get_intrinsic_decl(intrinsic).stub_diagnostic


def _bootstrap() -> None:
    declarations = (
        IntrinsicDecl("portable.elementwise_binary", 1, "portable", "elementwise_binary", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.matmul", 1, "portable", "matmul", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.load", 1, "portable", "load", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.store", 1, "portable", "store", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.cast", 1, "portable", "cast", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.broadcast", 1, "portable", "broadcast", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.transpose", 1, "portable", "transpose", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.view", 1, "portable", "view", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.reshape", 1, "portable", "reshape", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.reduction_sum", 1, "portable", "reduction_sum", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
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
        IntrinsicDecl("portable.channel_send", 1, "portable", "channel_send", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.channel_recv", 1, "portable", "channel_recv", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
        IntrinsicDecl("portable.allreduce", 1, "portable", "allreduce", "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC"),
    )
    for decl in declarations:
        register_intrinsic(decl)

    for intrinsic in (
        "portable.elementwise_binary",
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
        register_handlers("generic", intrinsic, simulate=True)
    register_handlers("nvgpu", "portable.elementwise_binary", lower=True, emit=True, simulate=True)
    register_handlers("nvgpu", "portable.matmul", lower=True, emit=True, simulate=True)
    register_handlers("pto", "portable.elementwise_binary", lower=True, emit=True, simulate=True)


_bootstrap()


__all__ = [
    "HandlerDecl",
    "IntrinsicDecl",
    "get_intrinsic_decl",
    "get_stub_diagnostic_code",
    "has_handler",
    "register_handlers",
    "register_intrinsic",
    "require_handler",
]
