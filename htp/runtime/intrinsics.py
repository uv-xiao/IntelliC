from __future__ import annotations

from collections.abc import Mapping

from .core import Runtime, _resolve_runtime


def register(name: str, handler, *, runtime: Runtime | None = None) -> None:
    _resolve_runtime(runtime).register_intrinsic(name, handler)


def invoke(
    name: str,
    *,
    args: tuple[object, ...],
    attrs: Mapping[str, object] | None = None,
    mode: str,
    trace: object | None = None,
    runtime: Runtime | None = None,
) -> object:
    return _resolve_runtime(runtime).invoke_intrinsic(
        name,
        args=args,
        attrs=attrs,
        mode=mode,
        trace=trace,
    )


__all__ = ["invoke", "register"]
