import pytest

from htp import compile_program
from htp.kernel import buffer, elementwise_mul, elementwise_unary, kernel, scalar


@kernel
def unsupported_fused_activation(
    gate: buffer(dtype="f32", shape=("size",), role="input"),
    up: buffer(dtype="f32", shape=("size",), role="input"),
    out: buffer(dtype="f32", shape=("size",), role="output"),
    size: scalar(dtype="i32", role="shape"),
) -> None:
    elementwise_unary("tanh", gate, out="gate_tanh", shape=(size,), dtype="f32")
    elementwise_mul("gate_tanh", up, out=out, shape=(size,), dtype="f32")


@pytest.mark.parametrize(
    ("target", "expected_detail"),
    (
        ("nvgpu-ampere", "Unsupported NV-GPU elementwise_unary operator 'tanh'."),
        ("pto-a2a3sim", "Unsupported PTO elementwise_unary operator 'tanh'."),
    ),
)
def test_fused_elementwise_emit_rejects_unknown_unary_operator(tmp_path, target, expected_detail):
    with pytest.raises(ValueError, match=expected_detail):
        compile_program(
            package_dir=tmp_path / target.replace("-", "_"),
            target=target,
            program=unsupported_fused_activation,
        )
