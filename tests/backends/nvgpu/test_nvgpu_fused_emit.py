import json

from htp import compile_program
from htp.kernel import buffer, elementwise_mul, kernel, scalar, sigmoid


@kernel
def swiglu(
    gate: buffer(dtype="f32", shape=("size",), role="input"),
    up: buffer(dtype="f32", shape=("size",), role="input"),
    out: buffer(dtype="f32", shape=("size",), role="output"),
    size: scalar(dtype="i32", role="shape"),
) -> None:
    sigmoid(gate, out="gate_sigmoid", shape=(size,), dtype="f32")
    elementwise_mul(gate, "gate_sigmoid", out="swish_gate", shape=(size,), dtype="f32")
    elementwise_mul("swish_gate", up, out=out, shape=(size,), dtype="f32")


def test_nvgpu_emit_supports_fused_elementwise_kernel(tmp_path):
    package = compile_program(package_dir=tmp_path / "nvgpu_swiglu", target="nvgpu-ampere", program=swiglu)

    codegen_index = json.loads((package.package_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json").read_text())
    kernel_source = (package.package_dir / "codegen" / "nvgpu" / "kernels" / "swiglu.cu").read_text()

    assert codegen_index["kernels"][0]["op"] == "fused_elementwise"
    assert [item["op"] for item in codegen_index["kernels"][0]["attrs"]["ops"]] == [
        "elementwise_unary",
        "elementwise_binary",
        "elementwise_binary",
    ]
    assert "expf(-gate[idx])" in kernel_source or "expf(-gate_value)" in kernel_source
    assert "out[idx] = out_value;" in kernel_source
