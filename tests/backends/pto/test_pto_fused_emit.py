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


def test_pto_emit_supports_fused_elementwise_kernel(tmp_path):
    package = compile_program(package_dir=tmp_path / "pto_swiglu", target="pto-a2a3sim", program=swiglu)

    codegen_index = json.loads((package.package_dir / "codegen" / "pto" / "pto_codegen.json").read_text())
    kernel_source = (package.package_dir / "codegen" / "pto" / "kernels" / "aiv" / "swiglu.cpp").read_text()
    orchestration_source = (package.package_dir / "codegen" / "pto" / "orchestration" / "swiglu_orchestration.cpp").read_text()

    assert codegen_index["kernels"][0]["op"] == "fused_elementwise"
    assert [item["op"] for item in codegen_index["kernels"][0]["attrs"]["ops"]] == [
        "elementwise_unary",
        "elementwise_binary",
        "elementwise_binary",
    ]
    assert "std::exp(-gate[index])" in kernel_source or "std::exp(-gate_value)" in kernel_source
    assert "runtime->add_task(kernel_args, 4, 0, CoreType::AIV);" in orchestration_source
