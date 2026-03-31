from __future__ import annotations

from htp.ir.build import program_module_from_kernels
from htp.ir.node_exec import NODE_KERNEL_INTERPRETER_ID
from htp.ir.nodes import (
    BinaryExpr,
    Kernel,
    NodeId,
    Return,
    from_payload,
    kernel,
    let,
    param,
    ref,
    region,
    to_payload,
)


def test_kernel_node_payload_round_trip():
    item = _demo_kernel()

    payload = to_payload(item)
    rebuilt = from_payload(payload)

    assert rebuilt == item


def test_kernel_node_interpreter_runs_program_module():
    module = program_module_from_kernels(_demo_kernel(), interpreter_id=NODE_KERNEL_INTERPRETER_ID)

    assert module.run(3, 4, bias=5, scale=2) == 24


def _demo_kernel() -> Kernel:
    x = param("n_param_x", "sym.x", "x", kind="scalar", dtype="f32")
    y = param("n_param_y", "sym.y", "y", kind="scalar", dtype="f32")
    bias = param("n_param_bias", "sym.bias", "bias", kind="scalar", dtype="f32")
    scale = param("n_param_scale", "sym.scale", "scale", kind="scalar", dtype="f32")
    return kernel(
        "item.affine_mix",
        "affine_mix",
        params=(x, y, bias, scale),
        body=region(
            "region.affine_mix",
            let(
                "n_sum",
                "sym.sum",
                "sum_xy",
                BinaryExpr(
                    node_id=NodeId("n_sum_expr"),
                    op="add",
                    lhs=ref("n_ref_x", "sym.x", "x"),
                    rhs=ref("n_ref_y", "sym.y", "y"),
                ),
            ),
            let(
                "n_shifted",
                "sym.shifted",
                "shifted",
                BinaryExpr(
                    node_id=NodeId("n_shifted_expr"),
                    op="add",
                    lhs=ref("n_ref_sum", "sym.sum", "sum_xy"),
                    rhs=ref("n_ref_bias", "sym.bias", "bias"),
                ),
            ),
            Return(
                node_id=NodeId("n_return"),
                value=BinaryExpr(
                    node_id=NodeId("n_scale_expr"),
                    op="mul",
                    lhs=ref("n_ref_shifted", "sym.shifted", "shifted"),
                    rhs=ref("n_ref_scale", "sym.scale", "scale"),
                ),
            ),
        ),
    )
