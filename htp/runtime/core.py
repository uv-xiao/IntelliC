from __future__ import annotations

from collections.abc import Callable, Mapping

from htp.intrinsics import get_stub_diagnostic_code, simulate_intrinsic

from .errors import ReplayDiagnosticError, raise_missing_kernel, raise_stub

KernelHandler = Callable[..., object]
IntrinsicHandler = Callable[..., object]
ExtensionHandler = Callable[..., object]


class Runtime:
    def __init__(
        self,
        *,
        kernels: Mapping[str, KernelHandler] | None = None,
        intrinsics: Mapping[str, IntrinsicHandler] | None = None,
        extensions: Mapping[tuple[str, str], ExtensionHandler] | None = None,
    ) -> None:
        self.kernel_handlers = dict(kernels or {})
        self.intrinsic_handlers = dict(intrinsics or {})
        self.extension_handlers = dict(extensions or {})
        self.channel_queues: dict[str, list[object]] = {}

    def register_kernel(self, kernel_id: str, handler: KernelHandler) -> None:
        self.kernel_handlers[kernel_id] = handler

    def register_intrinsic(self, name: str, handler: IntrinsicHandler) -> None:
        self.intrinsic_handlers[name] = handler

    def register_extension(self, extension_id: str, operation: str, handler: ExtensionHandler) -> None:
        self.extension_handlers[(extension_id, operation)] = handler

    def call_kernel(
        self,
        kernel_id: str,
        *,
        args: tuple[object, ...],
        mode: str,
        artifacts: Mapping[str, object],
        trace: object | None = None,
    ) -> object:
        handler = self.kernel_handlers.get(kernel_id)
        if handler is None:
            raise_missing_kernel(
                kernel_id,
                artifacts=artifacts,
                detail=f"No replay handler registered for kernel '{kernel_id}'",
            )
        return handler(args=args, mode=mode, artifacts=artifacts, trace=trace)

    def invoke_intrinsic(
        self,
        name: str,
        *,
        args: tuple[object, ...],
        attrs: Mapping[str, object] | None = None,
        mode: str,
        trace: object | None = None,
    ) -> object:
        handler = self.intrinsic_handlers.get(name)
        if handler is None:
            try:
                return simulate_intrinsic(
                    name,
                    args=args,
                    attrs=attrs,
                    mode=mode,
                    trace=trace,
                    runtime=self,
                )
            except ReplayDiagnosticError:
                raise
            except Exception:
                raise_stub(
                    get_stub_diagnostic_code(name),
                    node_id=f"intrinsic::{name}",
                    entity_id=name,
                    kind="intrinsic",
                    detail=f"No simulator registered for intrinsic '{name}'",
                )
        return handler(args=args, attrs=dict(attrs or {}), mode=mode, trace=trace)

    def invoke_extension(
        self,
        extension_id: str,
        operation: str,
        *,
        payload: Mapping[str, object],
        mode: str,
        trace: object | None = None,
    ) -> object:
        handler = self.extension_handlers.get((extension_id, operation))
        if handler is None:
            raise_stub(
                "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY",
                node_id=f"extension::{extension_id}::{operation}",
                entity_id=extension_id,
                kind="extension",
                detail=f"No replay handler registered for extension '{extension_id}:{operation}'",
            )
        return handler(payload=dict(payload), mode=mode, trace=trace)


_DEFAULT_RUNTIME: Runtime | None = None


def default_runtime() -> Runtime:
    global _DEFAULT_RUNTIME
    if _DEFAULT_RUNTIME is None:
        _DEFAULT_RUNTIME = Runtime()
    return _DEFAULT_RUNTIME


def _resolve_runtime(runtime: Runtime | None) -> Runtime:
    if runtime is not None:
        return runtime
    return default_runtime()


def call_kernel(
    kernel_id: str,
    *,
    args: tuple[object, ...],
    mode: str,
    artifacts: Mapping[str, object],
    trace: object | None = None,
    runtime: Runtime | None = None,
) -> object:
    return _resolve_runtime(runtime).call_kernel(
        kernel_id,
        args=args,
        mode=mode,
        artifacts=artifacts,
        trace=trace,
    )


__all__ = ["Runtime", "call_kernel", "default_runtime"]
