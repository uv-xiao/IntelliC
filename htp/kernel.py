"""Public kernel-authoring helpers for human-first HTP programs.

This module serves two audiences:

- public examples and high-level tests, which should read like ordinary Python
- low-level contract builders, which still need an explicit payload surface

The implementation therefore supports both a direct builder style and a more
native traced style via ``@kernel``.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from inspect import getclosurevars, signature
from typing import Any

from htp.types import (
    DType,
    TensorType,
    dims_payload,
    distribution_payload,
    dtype_name,
)

ScalarLiteral = int | float


@dataclass(frozen=True)
class KernelArgSpec:
    """Typed kernel argument surface that serializes into the canonical payload."""

    kind: str
    dtype: str
    shape: tuple[str, ...]
    role: str | None = None
    memory_space: str | None = None
    axis_layout: tuple[str, ...] = ()
    distribution: tuple[dict[str, Any], ...] = ()
    attrs: dict[str, Any] | None = None
    name: str | None = None

    def named(self, name: str) -> KernelArgSpec:
        return KernelArgSpec(
            name=name,
            kind=self.kind,
            dtype=self.dtype,
            shape=self.shape,
            role=self.role,
            memory_space=self.memory_space,
            axis_layout=self.axis_layout,
            distribution=self.distribution,
            attrs=None if self.attrs is None else dict(self.attrs),
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
        if self.memory_space is not None:
            payload["memory_space"] = self.memory_space
        if self.axis_layout:
            payload["axis_layout"] = list(self.axis_layout)
        if self.distribution:
            payload["distribution"] = [dict(item) for item in self.distribution]
        if self.attrs:
            payload["attrs"] = dict(self.attrs)
        return payload


@dataclass(frozen=True)
class KernelValue:
    """Symbolic value passed into traced kernel authoring functions."""

    name: str
    dtype: str | None = None
    shape: tuple[str, ...] = ()
    kind: str = "value"
    role: str | None = None
    memory_space: str | None = None
    axis_layout: tuple[str, ...] = ()
    distribution: tuple[dict[str, Any], ...] = ()
    attrs: dict[str, Any] | None = None

    def to_arg_payload(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "kind": self.kind,
            "dtype": self.dtype,
            "shape": list(self.shape),
        }
        if self.role is not None:
            payload["role"] = self.role
        if self.memory_space is not None:
            payload["memory_space"] = self.memory_space
        if self.axis_layout:
            payload["axis_layout"] = list(self.axis_layout)
        if self.distribution:
            payload["distribution"] = [dict(item) for item in self.distribution]
        if self.attrs:
            payload["attrs"] = dict(self.attrs)
        return payload

    def __add__(self, other: Operand) -> KernelValue:
        return _binary_expr("add", self, other)

    def __radd__(self, other: Operand) -> KernelValue:
        return _binary_expr("add", other, self)

    def __sub__(self, other: Operand) -> KernelValue:
        return _binary_expr("sub", self, other)

    def __rsub__(self, other: Operand) -> KernelValue:
        return _binary_expr("sub", other, self)

    def __mul__(self, other: Operand) -> KernelValue:
        return _binary_expr("mul", self, other)

    def __rmul__(self, other: Operand) -> KernelValue:
        return _binary_expr("mul", other, self)

    def __truediv__(self, other: Operand) -> KernelValue:
        return _binary_expr("div", self, other)

    def __rtruediv__(self, other: Operand) -> KernelValue:
        return _binary_expr("div", other, self)

    def __matmul__(self, other: KernelValue) -> KernelValue:
        return _matmul_expr(self, other)

    def __neg__(self) -> KernelValue:
        return _unary_expr("neg", self)


Operand = str | ScalarLiteral | KernelValue


@dataclass
class _KernelTrace:
    ops: list[dict[str, Any]]
    temp_index: int = 0


@dataclass(frozen=True)
class _RegionFrame:
    kind: str
    attrs: dict[str, Any]


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
_REGION_STACK: ContextVar[tuple[_RegionFrame, ...]] = ContextVar("htp_kernel_region_stack", default=())


def buffer(
    name: str | None = None,
    *,
    dtype: str | DType | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    role: str,
    type: TensorType | None = None,
    memory_space: str | None = None,
    axis_layout: tuple[str, ...] | list[str] = (),
    distribution: tuple[object, ...] | list[object] | None = None,
    attrs: dict[str, Any] | None = None,
) -> KernelArgSpec:
    dtype_name_value, shape_value, memory_space_value, axis_layout_value, distribution_value = (
        _resolve_buffer_type(
            dtype=dtype,
            shape=shape,
            type=type,
            memory_space=memory_space,
            axis_layout=axis_layout,
            distribution=distribution,
        )
    )
    return KernelArgSpec(
        name=name,
        kind="buffer",
        dtype=dtype_name_value,
        shape=shape_value,
        role=role,
        memory_space=memory_space_value,
        axis_layout=axis_layout_value,
        distribution=distribution_value,
        attrs=None if attrs is None else dict(attrs),
    )


def scalar(
    name: str | None = None,
    *,
    dtype: str | DType,
    role: str,
    attrs: dict[str, Any] | None = None,
) -> KernelArgSpec:
    return KernelArgSpec(
        name=name,
        kind="scalar",
        dtype=dtype_name(dtype),
        shape=(),
        role=role,
        attrs=None if attrs is None else dict(attrs),
    )


def value(
    name: str,
    *,
    kind: str = "buffer",
    dtype: str | DType | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    role: str | None = None,
    type: TensorType | None = None,
    memory_space: str | None = None,
    axis_layout: tuple[str, ...] | list[str] = (),
    distribution: tuple[object, ...] | list[object] | None = None,
    attrs: dict[str, Any] | None = None,
) -> KernelValue:
    dtype_name_value, shape_value, memory_space_value, axis_layout_value, distribution_value = (
        _resolve_buffer_type(
            dtype=dtype,
            shape=shape,
            type=type,
            memory_space=memory_space,
            axis_layout=axis_layout,
            distribution=distribution,
        )
    )
    return KernelValue(
        name=name,
        dtype=dtype_name_value,
        shape=shape_value,
        kind=kind,
        role=role,
        memory_space=memory_space_value,
        axis_layout=axis_layout_value,
        distribution=distribution_value,
        attrs=None if attrs is None else dict(attrs),
    )


def scratch(
    name: str | None = None,
    *,
    dtype: str | DType,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    memory_space: str,
    role: str = "temp",
    axis_layout: tuple[str, ...] | list[str] = (),
    attrs: dict[str, Any] | None = None,
) -> KernelValue:
    """Declare explicit scratch storage on the native kernel-value surface."""

    trace = _TRACE_RECORDER.get()
    resolved_name = name
    if resolved_name is None:
        if trace is None:
            raise ValueError("Implicit scratch names require traced @kernel execution.")
        resolved_name = _fresh_temp(trace, f"{memory_space}_scratch")
    return KernelValue(
        name=resolved_name,
        dtype=dtype_name(dtype),
        shape=_normalize_dims(shape),
        kind="buffer",
        role=role,
        memory_space=memory_space,
        axis_layout=tuple(str(item) for item in axis_layout),
        attrs=None if attrs is None else dict(attrs),
    )


def scratch_array(
    prefix: str,
    *,
    count: int,
    dtype: str | DType,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    memory_space: str,
    role: str = "temp",
    axis_layout: tuple[str, ...] | list[str] = (),
    attrs: dict[str, Any] | None = None,
) -> tuple[KernelValue, ...]:
    """Declare a fixed-size array of explicit scratch buffers."""

    if count <= 0:
        raise ValueError("scratch_array(...) requires count > 0.")
    return tuple(
        scratch(
            f"{prefix}_{index}",
            dtype=dtype,
            shape=shape,
            memory_space=memory_space,
            role=role,
            axis_layout=axis_layout,
            attrs=attrs,
        )
        for index in range(count)
    )


def shared(
    name: str | None = None,
    *,
    dtype: str | DType,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    role: str = "temp",
    axis_layout: tuple[str, ...] | list[str] = (),
    attrs: dict[str, Any] | None = None,
) -> KernelValue:
    """Declare one shared-memory scratch buffer."""

    return scratch(
        name,
        dtype=dtype,
        shape=shape,
        memory_space="shared",
        role=role,
        axis_layout=axis_layout,
        attrs=attrs,
    )


def shared_array(
    prefix: str,
    *,
    count: int,
    dtype: str | DType,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    role: str = "temp",
    axis_layout: tuple[str, ...] | list[str] = (),
    attrs: dict[str, Any] | None = None,
) -> tuple[KernelValue, ...]:
    """Declare a fixed-size array of shared-memory scratch buffers."""

    return scratch_array(
        prefix,
        count=count,
        dtype=dtype,
        shape=shape,
        memory_space="shared",
        role=role,
        axis_layout=axis_layout,
        attrs=attrs,
    )


def registers(
    name: str | None = None,
    *,
    dtype: str | DType,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    role: str = "temp",
    axis_layout: tuple[str, ...] | list[str] = (),
    attrs: dict[str, Any] | None = None,
) -> KernelValue:
    """Declare one register-backed scratch buffer."""

    return scratch(
        name,
        dtype=dtype,
        shape=shape,
        memory_space="register",
        role=role,
        axis_layout=axis_layout,
        attrs=attrs,
    )


def register_array(
    prefix: str,
    *,
    count: int,
    dtype: str | DType,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    role: str = "temp",
    axis_layout: tuple[str, ...] | list[str] = (),
    attrs: dict[str, Any] | None = None,
) -> tuple[KernelValue, ...]:
    """Declare a fixed-size array of register-backed scratch buffers."""

    return scratch_array(
        prefix,
        count=count,
        dtype=dtype,
        shape=shape,
        memory_space="register",
        role=role,
        axis_layout=axis_layout,
        attrs=attrs,
    )


@contextmanager
def region(kind: str, **attrs: Any):
    """Annotate subsequent traced ops with a named region frame."""

    current = _REGION_STACK.get()
    token = _REGION_STACK.set((*current, _RegionFrame(kind=str(kind), attrs=dict(attrs))))
    try:
        yield
    finally:
        _REGION_STACK.reset(token)


class _LoopIterable:
    """Iterable that annotates traced ops emitted inside Python `for` loops."""

    def __init__(self, iterable, *, modifier: str, name: str | None):
        self._iterable = iterable
        self._modifier = modifier
        self._name = name

    def __iter__(self):
        base_stack = _REGION_STACK.get()
        active_token = None
        try:
            for index, item in enumerate(self._iterable):
                if active_token is not None:
                    _REGION_STACK.reset(active_token)
                frame_attrs = {"modifier": self._modifier, "iteration": index}
                if self._name is not None:
                    frame_attrs["var"] = self._name
                if isinstance(item, (int, float, str)):
                    frame_attrs["value"] = item
                active_token = _REGION_STACK.set((*base_stack, _RegionFrame(kind="loop", attrs=frame_attrs)))
                yield item
        finally:
            if active_token is not None:
                _REGION_STACK.reset(active_token)


def unroll(iterable, *, name: str | None = None):
    """Annotate a Python `for` loop as an unrolled kernel loop."""

    return _LoopIterable(iterable, modifier="unroll", name=name)


def serial(iterable, *, name: str | None = None):
    """Annotate a Python `for` loop as a serial kernel loop."""

    return _LoopIterable(iterable, modifier="serial", name=name)


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
                memory_space=annotation.memory_space,
                axis_layout=annotation.axis_layout,
                distribution=annotation.distribution,
                attrs=None if annotation.attrs is None else dict(annotation.attrs),
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
    lhs: Operand,
    rhs: Operand,
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
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
            **_binary_operand_payload(lhs=lhs, rhs=rhs),
        },
        result=result,
    )


def elementwise_mul(
    lhs: Operand,
    rhs: Operand,
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
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
            **_binary_operand_payload(lhs=lhs, rhs=rhs),
        },
        result=result,
    )


def elementwise_sub(
    lhs: Operand,
    rhs: Operand,
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
        prefix="sub",
    )
    return _emit_or_return(
        {
            "op": "elementwise_binary",
            "operator": "sub",
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
            **_binary_operand_payload(lhs=lhs, rhs=rhs),
        },
        result=result,
    )


def elementwise_div(
    lhs: Operand,
    rhs: Operand,
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
        prefix="div",
    )
    return _emit_or_return(
        {
            "op": "elementwise_binary",
            "operator": "div",
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
            **_binary_operand_payload(lhs=lhs, rhs=rhs),
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
    out: str | KernelValue | None = None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue],
    dtype: str,
) -> dict[str, Any] | KernelValue:
    result = _resolve_result_value(
        out=out,
        shape=shape,
        dtype=dtype,
        sources=(source,),
        prefix="broadcast",
    )
    return _emit_or_return(
        {
            "op": "broadcast",
            "source": _ref(source),
            "out": result.name,
            "shape": list(result.shape),
            "dtype": result.dtype,
        },
        result=result,
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
    source: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    axis: str | int,
    dtype: str,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
) -> dict[str, Any] | KernelValue:
    resolved_shape = shape
    if resolved_shape is None and out is None:
        resolved_shape = _infer_reduction_shape(source, axis)
    result = _resolve_result_value(
        out=out,
        shape=resolved_shape,
        dtype=dtype,
        sources=(source,),
        prefix="reduce_sum",
    )
    return _emit_or_return(
        {
            "op": "reduction_sum",
            "source": _ref(source),
            "out": result.name,
            "axis": axis,
            "dtype": result.dtype,
        },
        result=result,
    )


def slice_tensor(
    source: str | KernelValue,
    *,
    out: str | KernelValue,
    offsets: tuple[int, ...] | list[int],
    sizes: tuple[str | KernelValue | int, ...] | list[str | KernelValue | int],
    dtype: str | DType,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "slice",
            "source": _ref(source),
            "out": _ref(out),
            "offsets": list(offsets),
            "sizes": [str(_ref(item)) for item in sizes],
            "dtype": dtype_name(dtype),
        }
    )


def concat(
    *inputs: str | KernelValue,
    out: str | KernelValue,
    axis: int,
    dtype: str | DType,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "concat",
            "inputs": [str(_ref(item)) for item in inputs],
            "out": _ref(out),
            "axis": axis,
            "dtype": dtype_name(dtype),
        }
    )


def async_copy(
    source: str | KernelValue,
    *,
    target: str | KernelValue | None = None,
    dtype: str,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
    memory_space: str | None = None,
) -> dict[str, Any] | KernelValue:
    source_value = _require_kernel_value(source, op_name="async_copy") if target is None else None
    if target is None:
        trace = _TRACE_RECORDER.get()
        if trace is None:
            raise ValueError("Implicit async_copy targets require traced @kernel execution.")
        result = KernelValue(
            name=_fresh_temp(trace, "copy"),
            dtype=dtype,
            shape=_normalize_dims(shape) if shape is not None else source_value.shape,
            kind=source_value.kind,
            memory_space=memory_space or "shared",
            axis_layout=source_value.axis_layout,
        )
    else:
        result = _resolve_result_value(
            out=target,
            shape=shape,
            dtype=dtype,
            sources=(source,),
            prefix="copy",
        )
        if result.memory_space is None and memory_space is not None:
            result = KernelValue(
                name=result.name,
                dtype=result.dtype,
                shape=result.shape,
                kind=result.kind,
                role=result.role,
                memory_space=memory_space,
                axis_layout=result.axis_layout,
                attrs=None if result.attrs is None else dict(result.attrs),
            )
    payload = {
        "op": "async_copy",
        "source": _ref(source),
        "target": result.name,
        "dtype": result.dtype,
    }
    if result.shape:
        payload["shape"] = list(result.shape)
    if result.memory_space is not None:
        payload["target_memory_space"] = result.memory_space
    return _emit_or_return(payload, result=result)


def mma(
    lhs: str | KernelValue,
    rhs: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    m: str | KernelValue | None = None,
    n: str | KernelValue | None = None,
    k: str | KernelValue | None = None,
    dtype: str,
) -> dict[str, Any] | KernelValue:
    inferred_m, inferred_n, inferred_k, inferred_shape = _infer_matmul_shape(lhs, rhs)
    result = _resolve_result_value(
        out=out,
        shape=inferred_shape,
        dtype=dtype,
        sources=(lhs, rhs),
        prefix="mma",
    )
    return _emit_or_return(
        {
            "op": "mma",
            "lhs": _ref(lhs),
            "rhs": _ref(rhs),
            "out": result.name,
            "m": _ref(m if m is not None else inferred_m),
            "n": _ref(n if n is not None else inferred_n),
            "k": _ref(k if k is not None else inferred_k),
            "dtype": result.dtype,
        },
        result=result,
    )


def channel_send(value: str | KernelValue, *, channel: str | KernelValue) -> dict[str, Any]:
    return _emit_or_return({"op": "channel_send", "value": _ref(value), "channel": _ref(channel)})


def channel_recv(
    channel: str | KernelValue,
    *,
    out: str | KernelValue | None = None,
    dtype: str,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None = None,
) -> dict[str, Any] | KernelValue:
    result = _resolve_result_value(
        out=out,
        shape=shape or (),
        dtype=dtype,
        sources=(),
        prefix="recv",
    )
    return _emit_or_return(
        {
            "op": "channel_recv",
            "channel": _ref(channel),
            "out": result.name,
            "dtype": result.dtype,
        },
        result=result,
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


def allgather(
    source: str | KernelValue,
    *,
    out: str | KernelValue,
    axis: int,
    mesh_axis: int | str,
    dtype: str | DType,
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "allgather",
            "source": _ref(source),
            "out": _ref(out),
            "axis": axis,
            "mesh_axis": mesh_axis,
            "dtype": dtype_name(dtype),
        }
    )


def reduce_scatter(
    source: str | KernelValue,
    *,
    out: str | KernelValue,
    axis: int,
    mesh_axis: int | str,
    dtype: str | DType,
    op: str = "sum",
) -> dict[str, Any]:
    return _emit_or_return(
        {
            "op": "reduce_scatter",
            "source": _ref(source),
            "out": _ref(out),
            "axis": axis,
            "mesh_axis": mesh_axis,
            "reduction": op,
            "dtype": dtype_name(dtype),
        }
    )


def barrier() -> dict[str, Any]:
    return _emit_or_return({"op": "barrier"})


def await_token(token: str | KernelValue) -> dict[str, Any]:
    return _emit_or_return({"op": "await", "token": _ref(token)})


def _emit_or_return(op: dict[str, Any], *, result: KernelValue | None = None) -> dict[str, Any] | KernelValue:
    region_payload = _active_regions_payload()
    if region_payload:
        attrs = dict(op.get("attrs", {})) if isinstance(op.get("attrs"), dict) else {}
        attrs["regions"] = region_payload
        op = {**op, "attrs": attrs}
    recorder = _TRACE_RECORDER.get()
    if recorder is not None:
        recorder.ops.append(op)
        return result if result is not None else op
    return op


def _binary_expr(operator: str, lhs: Operand, rhs: Operand) -> KernelValue:
    if operator == "add":
        result = elementwise_add(lhs, rhs)
    elif operator == "sub":
        result = elementwise_sub(lhs, rhs)
    elif operator == "mul":
        result = elementwise_mul(lhs, rhs)
    elif operator == "div":
        result = elementwise_div(lhs, rhs)
    else:
        raise ValueError(f"Unsupported binary operator {operator!r}.")
    if not isinstance(result, KernelValue):
        raise RuntimeError("Expression-form binary ops require traced kernel execution.")
    return result


def _binary_operand_payload(*, lhs: Operand, rhs: Operand) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if _is_scalar_literal(lhs):
        payload["lhs_const"] = float(lhs)
    else:
        payload["lhs"] = _ref(lhs)
    if _is_scalar_literal(rhs):
        payload["rhs_const"] = float(rhs)
    else:
        payload["rhs"] = _ref(rhs)
    return payload


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
    sources: tuple[Operand, ...],
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
            memory_space=out.memory_space,
            axis_layout=out.axis_layout,
            distribution=out.distribution,
            attrs=None if out.attrs is None else dict(out.attrs),
        )
    return KernelValue(name=out, dtype=resolved_dtype, shape=resolved_shape)


def _first_kernel_value(values: tuple[Operand, ...]) -> KernelValue | None:
    for value in values:
        if isinstance(value, KernelValue):
            return value
    return None


def _fresh_temp(trace: _KernelTrace, prefix: str) -> str:
    name = f"{prefix}_{trace.temp_index}"
    trace.temp_index += 1
    return name


def _active_regions_payload() -> list[dict[str, Any]]:
    stack = _REGION_STACK.get()
    return [{"kind": item.kind, **dict(item.attrs)} for item in stack]


def _as_named_value(value: str | KernelValue, *, fallback: KernelValue | None = None) -> KernelValue:
    if isinstance(value, KernelValue):
        return value
    if fallback is not None:
        return KernelValue(
            name=value,
            dtype=fallback.dtype,
            shape=fallback.shape,
            kind=fallback.kind,
            role=fallback.role,
            memory_space=fallback.memory_space,
            axis_layout=fallback.axis_layout,
            distribution=fallback.distribution,
            attrs=None if fallback.attrs is None else dict(fallback.attrs),
        )
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


def _infer_reduction_shape(
    source: str | KernelValue,
    axis: str | int,
) -> tuple[str, ...]:
    source_value = _require_kernel_value(source, op_name="reduction_sum")
    dims = list(source_value.shape)
    if not dims:
        return ()
    if isinstance(axis, int):
        if axis < 0 or axis >= len(dims):
            raise ValueError("Reduction axis is out of bounds for the symbolic source shape.")
        return tuple(dim for index, dim in enumerate(dims) if index != axis)
    return tuple(dim for dim in dims if dim != str(axis))


def _require_kernel_value(value: str | KernelValue, *, op_name: str) -> KernelValue:
    if isinstance(value, KernelValue):
        return value
    raise ValueError(f"Expression-form {op_name} requires typed symbolic operands, not raw strings.")


def _ref(value: str | KernelValue | int | float) -> str | int | float:
    if isinstance(value, KernelValue):
        return value.name
    return value


def _is_scalar_literal(value: Operand) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _normalize_dims(
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None,
) -> tuple[str, ...]:
    if shape is None:
        return ()
    return tuple(str(_ref(dim)) for dim in shape)


def _resolve_buffer_type(
    *,
    dtype: str | DType | None,
    shape: tuple[str | KernelValue, ...] | list[str | KernelValue] | None,
    type: TensorType | None,
    memory_space: str | None,
    axis_layout: tuple[str, ...] | list[str],
    distribution: tuple[object, ...] | list[object] | None,
) -> tuple[str, tuple[str, ...], str | None, tuple[str, ...], tuple[dict[str, Any], ...]]:
    if type is not None:
        return (
            dtype_name(type.dtype),
            dims_payload(type.shape),
            type.memory_space if memory_space is None else memory_space,
            type.axis_layout if not axis_layout else tuple(str(item) for item in axis_layout),
            distribution_payload(type.distribution if distribution is None else distribution),
        )
    if dtype is None:
        raise TypeError("buffer/value requires either dtype=... or type=...")
    return (
        dtype_name(dtype),
        _normalize_dims(shape),
        memory_space,
        tuple(str(item) for item in axis_layout),
        distribution_payload(distribution),
    )


def _resolve_annotation(annotation: Any, *, function: Callable[..., Any]) -> Any:
    if isinstance(annotation, str):
        closure = getclosurevars(function)
        namespace = dict(function.__globals__)
        namespace.update(closure.globals)
        namespace.update(closure.nonlocals)
        return eval(annotation, namespace, namespace)
    return annotation


__all__ = [
    "KernelArgSpec",
    "KernelSpec",
    "KernelValue",
    "allreduce",
    "allgather",
    "async_copy",
    "await_token",
    "barrier",
    "broadcast",
    "buffer",
    "cast",
    "channel_recv",
    "channel_send",
    "concat",
    "elementwise_add",
    "elementwise_div",
    "elementwise_mul",
    "elementwise_sub",
    "elementwise_unary",
    "exp",
    "kernel",
    "matmul",
    "mma",
    "recip",
    "reduce_scatter",
    "reduction_sum",
    "region",
    "relayout",
    "register_array",
    "registers",
    "reshape",
    "scalar",
    "scratch",
    "scratch_array",
    "serial",
    "shared",
    "shared_array",
    "sigmoid",
    "slice_tensor",
    "store",
    "transpose",
    "unroll",
    "value",
]
