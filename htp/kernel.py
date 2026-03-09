"""Public kernel-authoring helpers for human-first HTP programs.

This module serves two audiences:

- public examples and high-level tests, which should read like ordinary Python
- low-level contract builders, which still need an explicit payload surface

The implementation therefore supports both a direct builder style and a more
native traced style via ``@kernel``.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from inspect import signature
from typing import Any, Callable


@dataclass(frozen=True)
class KernelArgSpec:
    """Typed kernel argument surface that serializes into the canonical payload."""

    kind: str
    dtype: str
    shape: tuple[str, ...]
    role: str | None = None
    name: str | None = None

    def named(self, name: str) -> "KernelArgSpec":
        return KernelArgSpec(
            name=name,
            kind=self.kind,
            dtype=self.dtype,
            shape=self.shape,
            role=self.role,
        )

    def to_payload(self) -> dict[str, Any]:
        if self.name is None:
            raise ValueError("KernelArgSpec must have a name before it can be serialized")
        payload = {
            "name": self.name,
            "kind": self.kind,
            "dtype": self.dtype,
            "shape": list(self.shape),
        }
        if self.role is not None:
            payload["role"] = self.role
        return payload


@dataclass(frozen=True)
class KernelValue:
    """Symbolic value passed into traced kernel authoring functions."""

    name: str


@dataclass(frozen=True)
class KernelSpec:
    """Public kernel surface that can lower into the canonical program payload."""

    name: str
    args: tuple[KernelArgSpec, ...]
    ops: tuple[dict[str, Any], ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "args": [argument.to_payload() for argument in self.args],
            "ops": [dict(op) for op in self.ops],
        }

    def to_program(self) -> dict[str, Any]:
        shape_args = [argument.name for argument in self.args if argument.role == "shape" and argument.name is not None]
        runtime_args = [argument.name for argument in self.args if argument.name is not None]
        return {
            "entry": self.name,
            "kernel": self.to_payload(),
            "workload": {
                "entry": self.name,
                "tasks": [
                    {
                        "task_id": "task0",
                        "kind": "kernel_call",
                        "kernel": self.name,
                        "args": runtime_args,
                    }
                ],
                "channels": [],
                "dependencies": [],
            },
            "analysis": {},
            "package": {"emitted": False},
            "entry_signature": {"shape_args": shape_args},
        }


_TRACE_RECORDER: ContextVar[list[dict[str, Any]] | None] = ContextVar("htp_kernel_trace_recorder", default=None)


def buffer(
    name: str | None = None,
    *,
    dtype: str,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    role: str,
) -> KernelArgSpec:
    return KernelArgSpec(name=name, kind="buffer", dtype=dtype, shape=_normalize_dims(shape), role=role)


def scalar(name: str | None = None, *, dtype: str, role: str) -> KernelArgSpec:
    return KernelArgSpec(name=name, kind="scalar", dtype=dtype, shape=(), role=role)


def kernel(
    arg: str | Callable[..., Any],
    *,
    args: list[KernelArgSpec] | tuple[KernelArgSpec, ...] | None = None,
    ops: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
) -> KernelSpec | Callable[..., KernelSpec]:
    if callable(arg) and args is None and ops is None:
        return _trace_kernel(arg)
    if not isinstance(arg, str) or args is None or ops is None:
        raise TypeError("kernel(...) expects either a function decorator usage or name=string with args= and ops=")
    return KernelSpec(name=arg, args=tuple(args), ops=tuple(dict(op) for op in ops))


def _trace_kernel(function: Callable[..., Any]) -> KernelSpec:
    parameters = signature(function).parameters
    args: list[KernelArgSpec] = []
    call_values: list[KernelValue] = []
    for parameter_name, parameter in parameters.items():
        annotation = _resolve_annotation(parameter.annotation, function=function)
        if not isinstance(annotation, KernelArgSpec):
            raise TypeError(
                f"Traced kernel parameter {parameter_name!r} must use htp.kernel.buffer(...) or htp.kernel.scalar(...) annotation"
            )
        args.append(annotation.named(parameter_name))
        call_values.append(KernelValue(parameter_name))
    token = _TRACE_RECORDER.set([])
    try:
        function(*call_values)
        recorded = _TRACE_RECORDER.get() or []
    finally:
        _TRACE_RECORDER.reset(token)
    return KernelSpec(name=function.__name__, args=tuple(args), ops=tuple(recorded))


def elementwise_add(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    dtype: str,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "elementwise_binary",
            "operator": "add",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": _ref(out),
            "shape": _normalize_dims(shape),
            "dtype": dtype,
        }
    )


def elementwise_mul(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    dtype: str,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "elementwise_binary",
            "operator": "mul",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": _ref(out),
            "shape": _normalize_dims(shape),
            "dtype": dtype,
        }
    )


def matmul(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue,
    m: str | KernelValue,
    n: str | KernelValue,
    k: str | KernelValue,
    dtype: str,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "matmul",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": _ref(out),
            "m": _ref(m),
            "n": _ref(n),
            "k": _ref(k),
            "dtype": dtype,
        }
    )


def cast(source: str | KernelValue, *, out: str | KernelValue, dtype: str) -> dict[str, Any]:
    return _emit_or_return({"op": "cast", "source": _ref(source), "out": _ref(out), "dtype": dtype})


def broadcast(
    source: str | KernelValue,
    *,
    out: str | KernelValue,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    dtype: str,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "broadcast",
            "source": _ref(source),
            "out": _ref(out),
            "shape": _normalize_dims(shape),
            "dtype": dtype,
        }
    )


def transpose(
    source: str | KernelValue,
    *,
    out: str | KernelValue,
    permutation: tuple[int, ...] | list[int],
    dtype: str,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "transpose",
            "source": _ref(source),
            "out": _ref(out),
            "permutation": list(permutation),
            "dtype": dtype,
        }
    )


def reshape(
    source: str | KernelValue,
    *,
    out: str | KernelValue,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    dtype: str,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "reshape",
            "source": _ref(source),
            "out": _ref(out),
            "shape": _normalize_dims(shape),
            "dtype": dtype,
        }
    )


def relayout(source: str | KernelValue, *, out: str | KernelValue, layout: str, dtype: str) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "relayout",
            "source": _ref(source),
            "out": _ref(out),
            "layout": layout,
            "dtype": dtype,
        }
    )


def reduction_sum(
    source: str | KernelValue, *, out: str | KernelValue, axis: str | int, dtype: str
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "reduction_sum",
            "source": _ref(source),
            "out": _ref(out),
            "axis": axis,
            "dtype": dtype,
        }
    )


def async_copy(source: str | KernelValue, *, target: str | KernelValue, dtype: str) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "async_copy",
            "source": _ref(source),
            "target": _ref(target),
            "dtype": dtype,
        }
    )


def mma(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue,
    m: str | KernelValue,
    n: str | KernelValue,
    k: str | KernelValue,
    dtype: str,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "mma",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": _ref(out),
            "m": _ref(m),
            "n": _ref(n),
            "k": _ref(k),
            "dtype": dtype,
        }
    )


def channel_send(value: str | KernelValue, *, channel: str | KernelValue) -> dict[str, Any]:
    return _emit_or_return({"op": "channel_send", "value": _ref(value), "channel": _ref(channel)})


def channel_recv(channel: str | KernelValue, *, out: str | KernelValue, dtype: str) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "channel_recv",
            "channel": _ref(channel),
            "out": _ref(out),
            "dtype": dtype,
        }
    )


def allreduce(source: str | KernelValue, *, out: str | KernelValue, op: str, dtype: str) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "allreduce",
            "source": _ref(source),
            "out": _ref(out),
            "reduction": op,
            "dtype": dtype,
        }
    )


def barrier() -> dict[str, Any]:
    return _emit_or_return({"op": "barrier"})


def await_token(token: str | KernelValue) -> dict[str, Any]:
    return _emit_or_return({"op": "await", "token": _ref(token)})


def _emit_or_return(op: dict[str, Any]) -> dict[str, Any]:
    recorder = _TRACE_RECORDER.get()
    if recorder is not None:
        recorder.append(op)
    return op


def _ref(value: str | KernelValue | int) -> str | int:
    if isinstance(value, KernelValue):
        return value.name
    return value


def _normalize_dims(shape: tuple[str | KernelValue, ...] | list[str | KernelValue]) -> tuple[str, ...]:
    return tuple(str(_ref(dim)) for dim in shape)


def _resolve_annotation(annotation: Any, *, function: Callable[..., Any]) -> Any:
    if isinstance(annotation, str):
        return eval(annotation, function.__globals__, function.__globals__)
    return annotation


__all__ = [
    "KernelArgSpec",
    "KernelSpec",
    "KernelValue",
    "allreduce",
    "async_copy",
    "await_token",
    "barrier",
    "broadcast",
    "buffer",
    "cast",
    "channel_recv",
    "channel_send",
    "elementwise_add",
    "elementwise_mul",
    "kernel",
    "matmul",
    "mma",
    "reduction_sum",
    "relayout",
    "reshape",
    "scalar",
    "transpose",
]
