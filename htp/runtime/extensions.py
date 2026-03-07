from __future__ import annotations

from collections.abc import Mapping

from .core import Runtime, _resolve_runtime


def register(extension_id: str, operation: str, handler, *, runtime: Runtime | None = None) -> None:
    _resolve_runtime(runtime).register_extension(extension_id, operation, handler)


def invoke(
    extension_id: str,
    operation: str,
    *,
    payload: Mapping[str, object],
    mode: str,
    trace: object | None = None,
    runtime: Runtime | None = None,
) -> object:
    return _resolve_runtime(runtime).invoke_extension(
        extension_id,
        operation,
        payload=payload,
        mode=mode,
        trace=trace,
    )


__all__ = ["invoke", "register"]
