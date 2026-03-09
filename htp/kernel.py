"""Public kernel-authoring helpers for human-first HTP programs.

This module serves two audiences:

- public examples and high-level tests, which should read like ordinary Python
- low-level contract builders, which still need an explicit payload surface

The implementation therefore supports both a direct builder style and a more
native traced style via ``@kernel``.
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from inspect import signature
from typing import Any


@dataclass(frozen=True)
class KernelArgSpec:
    """Typed kernel argument surface that serializes into the canonical payload."""

    kind: str
    dtype: str
    shape: tuple[str, ...]
    role: str | None = None
    name: str | None = None

    def named(self, name: str) -> KernelArgSpec:
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
    dtype: str | None = None
    shape: tuple[str, ...] = ()
    kind: str = "value"
    role: str | None = None

    def __add__(self, other: KernelValue) -> KernelValue:
        return _binary_expr("add", self, other)

    def __mul__(self, other: KernelValue) -> KernelValue:
        return _binary_expr("mul", self, other)

    def __matmul__(self, other: KernelValue) -> KernelValue:
        return _matmul_expr(self, other)

    def __neg__(self) -> KernelValue:
        return _unary_expr("neg", self)


@dataclass
class _KernelTrace:
    ops: list[dict[str, Any]]
    temp_index: int = 0


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
        shape_args = [
            argument.name for argument in self.args if argument.role == "shape" and argument.name is not None
        ]
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


_TRACE_RECORDER: ContextVar[_KernelTrace | None] = ContextVar("htp_kernel_trace_recorder", default=None)


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
        raise TypeError(
            "kernel(...) expects either a function decorator usage or name=string with args= and ops="
        )
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
        call_values.append(
            KernelValue(
                parameter_name,
                dtype=annotation.dtype,
                shape=annotation.shape,
                kind=annotation.kind,
                role=annotation.role,
            )
        )
    token = _TRACE_RECORDER.set(_KernelTrace(ops=[]))
    try:
        function(*call_values)
        trace = _TRACE_RECORDER.get()
        recorded = [] if trace is None else trace.ops
    finally:
        _TRACE_RECORDER.reset(token)
    return KernelSpec(name=function.__name__, args=tuple(args), ops=tuple(recorded))


def elementwise_add(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    dtype: str | None = None,
) -> dict[str, Any] | KernelValue:
    result = _resolve_result_value(
        out=out,
        shape=shape,
        dtype=dtype,
        sources=(lhs, rhs),
        prefix="add",
    )
    return _emit_or_return(
        {
            "op": "elementwise_binary",
            "operator": "add",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
        },
        result=result,
    )


def elementwise_mul(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    dtype: str | None = None,
) -> dict[str, Any] | KernelValue:
    result = _resolve_result_value(
        out=out,
        shape=shape,
        dtype=dtype,
        sources=(lhs, rhs),
        prefix="mul",
    )
    return _emit_or_return(
        {
            "op": "elementwise_binary",
            "operator": "mul",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
        },
        result=result,
    )


def elementwise_unary(
    operator: str,
    source: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    dtype: str | None = None,
) -> dict[str, Any] | KernelValue:
    result = _resolve_result_value(
        out=out,
        shape=shape,
        dtype=dtype,
        sources=(source,),
        prefix=operator,
    )
    return _emit_or_return(
        {
            "op": "elementwise_unary",
            "operator": operator,
            "source": _ref(source),
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
        },
        result=result,
    )


def matmul(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    m: str | KernelValue | None = None,
    n: str | KernelValue | None = None,
    k: str | KernelValue | None = None,
    dtype: str | None = None,
) -> dict[str, Any] | KernelValue:
    inferred_m, inferred_n, inferred_k, inferred_shape = _infer_matmul_shape(lhs, rhs)
    result = _resolve_result_value(
        out=out,
        shape=inferred_shape,
        dtype=dtype,
        sources=(lhs, rhs),
        prefix="matmul",
    )
    return _emit_or_return(
        {
            "op": "matmul",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": result.name,
            "m": _ref(m if m is not None else inferred_m),
            "n": _ref(n if n is not None else inferred_n),
            "k": _ref(k if k is not None else inferred_k),
            "shape": list(result.shape),
            "dtype": result.dtype,
        },
        result=result,
    )


def cast(source: str | KernelValue, *, out: str | KernelValue, dtype: str) -> dict[str, Any]:
    return _emit_or_return({"op": "cast", "source": _ref(source), "out": _ref(out), "dtype": dtype})


def exp(
    source: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    dtype: str | None = None,
) -> dict[str, Any] | KernelValue:
    return elementwise_unary("exp", source, out=out, shape=shape, dtype=dtype)


def recip(
    source: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    dtype: str | None = None,
) -> dict[str, Any] | KernelValue:
    return elementwise_unary("recip", source, out=out, shape=shape, dtype=dtype)


def sigmoid(
    source: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    dtype: str | None = None,
) -> dict[str, Any] | KernelValue:
    return elementwise_unary("sigmoid", source, out=out, shape=shape, dtype=dtype)


def store(target: str | KernelValue, value: str | KernelValue) -> dict[str, Any] | KernelValue:
    target_value = _as_named_value(target)
    source_value = _as_named_value(value, fallback=target_value)
    return elementwise_unary(
        "identity",
        source_value,
        out=target_value,
        shape=target_value.shape,
        dtype=target_value.dtype,
    )


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


def _emit_or_return(op: dict[str, Any], *, result: KernelValue | None = None) -> dict[str, Any] | KernelValue:
    recorder = _TRACE_RECORDER.get()
    if recorder is not None:
        recorder.ops.append(op)
        return result if result is not None else op
    return op


def _binary_expr(operator: str, lhs: KernelValue, rhs: KernelValue) -> KernelValue:
    if operator == "add":
        result = elementwise_add(lhs, rhs)
    elif operator == "mul":
        result = elementwise_mul(lhs, rhs)
    else:
        raise ValueError(f"Unsupported binary operator {operator!r}.")
    if not isinstance(result, KernelValue):
        raise RuntimeError("Expression-form binary ops require traced kernel execution.")
    return result


def _unary_expr(operator: str, source: KernelValue) -> KernelValue:
    result = elementwise_unary(operator, source)
    if not isinstance(result, KernelValue):
        raise RuntimeError("Expression-form unary ops require traced kernel execution.")
    return result


def _matmul_expr(lhs: KernelValue, rhs: KernelValue) -> KernelValue:
    result = matmul(lhs, rhs)
    if not isinstance(result, KernelValue):
        raise RuntimeError("Expression-form matmul requires traced kernel execution.")
    return result


def _resolve_result_value(
    *,
    out: str | KernelValue | None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | tuple[str, ...] | None,
    dtype: str | None,
    sources: tuple[str | KernelValue, ...],
    prefix: str,
) -> KernelValue:
    source_value = _first_kernel_value(sources)
    resolved_shape = (
        tuple(_normalize_dims(shape))
        if shape is not None
        else (source_value.shape if source_value is not None else ())
    )
    resolved_dtype = (
        dtype if dtype is not None else (source_value.dtype if source_value is not None else None)
    )
    if resolved_dtype is None:
        raise ValueError("Expression-form kernel ops require dtype or a typed symbolic source.")
    if out is None:
        trace = _TRACE_RECORDER.get()
        if trace is None:
            raise ValueError("Implicit temporary kernel values require traced @kernel execution.")
        return KernelValue(name=_fresh_temp(trace, prefix), dtype=resolved_dtype, shape=resolved_shape)
    if isinstance(out, KernelValue):
        return KernelValue(
            name=out.name,
            dtype=resolved_dtype if out.dtype is None else out.dtype,
            shape=resolved_shape if not out.shape else out.shape,
            kind=out.kind,
            role=out.role,
        )
    return KernelValue(name=out, dtype=resolved_dtype, shape=resolved_shape)


def _first_kernel_value(values: tuple[str | KernelValue, ...]) -> KernelValue | None:
    for value in values:
        if isinstance(value, KernelValue):
            return value
    return None


def _fresh_temp(trace: _KernelTrace, prefix: str) -> str:
    name = f"{prefix}_{trace.temp_index}"
    trace.temp_index += 1
    return name


def _as_named_value(value: str | KernelValue, *, fallback: KernelValue | None = None) -> KernelValue:
    if isinstance(value, KernelValue):
        return value
    if fallback is not None:
        return KernelValue(name=value, dtype=fallback.dtype, shape=fallback.shape)
    raise ValueError("String-only kernel references require a typed fallback.")


def _infer_matmul_shape(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
) -> tuple[str | int, str | int, str | int, tuple[str, ...]]:
    lhs_value = _require_kernel_value(lhs, op_name="matmul")
    rhs_value = _require_kernel_value(rhs, op_name="matmul")
    if len(lhs_value.shape) != 2 or len(rhs_value.shape) != 2:
        raise ValueError("Expression-form matmul requires rank-2 typed operands.")
    lhs_m, lhs_k = lhs_value.shape
    rhs_k, rhs_n = rhs_value.shape
    if lhs_k != rhs_k:
        raise ValueError("Expression-form matmul requires matching contraction dimensions.")
    return lhs_m, rhs_n, lhs_k, (lhs_m, rhs_n)


def _require_kernel_value(value: str | KernelValue, *, op_name: str) -> KernelValue:
    if isinstance(value, KernelValue):
        return value
    raise ValueError(f"Expression-form {op_name} requires typed symbolic operands, not raw strings.")


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
    "elementwise_unary",
    "exp",
    "kernel",
    "matmul",
    "mma",
    "recip",
    "reduction_sum",
    "relayout",
    "reshape",
    "scalar",
    "sigmoid",
    "store",
    "transpose",
]
