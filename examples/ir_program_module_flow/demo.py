from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from htp.ir.core.nodes import (
    BinaryExpr,
    ItemId,
    Kernel,
    NodeId,
    Return,
    channel,
    item_ref,
    kernel,
    let,
    literal,
    param,
    process,
    process_graph,
    process_step,
    ref,
    region,
)
from htp.ir.core.semantics import KernelIR, WorkloadIR, WorkloadTask
from htp.ir.frontends import resolve_frontend
from htp.ir.interpreters.entrypoints import NODE_KERNEL_INTERPRETER_ID, NODE_PROCESS_GRAPH_INTERPRETER_ID
from htp.ir.program.build import program_module_from_items, program_module_from_kernels
from htp.ir.program.render import render_program_module_payload
from htp.kernel import KernelSpec


def define_program() -> Any:
    x = param("n_param_x", "sym.x", "x", kind="scalar", dtype="f32")
    y = param("n_param_y", "sym.y", "y", kind="scalar", dtype="f32")
    bias = param("n_param_bias", "sym.bias", "bias", kind="scalar", dtype="f32")
    scale = param("n_param_scale", "sym.scale", "scale", kind="scalar", dtype="f32")

    affine_mix = kernel(
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

    return program_module_from_kernels(
        affine_mix,
        entry="run",
        interpreter_id=NODE_KERNEL_INTERPRETER_ID,
        analyses={
            "demo.shape": {
                "schema": "htp.analysis.demo_shape.v1",
                "kernel": "affine_mix",
                "steps": ["sum_xy", "shifted", "return"],
            }
        },
        meta={"source": "examples/ir_program_module_flow/demo.py"},
    )


def transform_program(module: Any) -> Any:
    del module
    x = param("n_param_x2", "sym.x", "x", kind="scalar", dtype="f32")
    y = param("n_param_y2", "sym.y", "y", kind="scalar", dtype="f32")
    bias = param("n_param_bias2", "sym.bias", "bias", kind="scalar", dtype="f32")

    transformed_kernel = Kernel(
        node_id=NodeId("node.item.affine_mix_fused"),
        item_id=ItemId("item.affine_mix_fused"),
        name="affine_mix_fused",
        params=(x, y, bias),
        body=region(
            "region.affine_mix_fused",
            let(
                "n_weighted_x",
                "sym.weighted_x",
                "weighted_x",
                BinaryExpr(
                    node_id=NodeId("n_weighted_x_expr"),
                    op="mul",
                    lhs=ref("n_ref_x_2", "sym.x", "x"),
                    rhs=literal("n_two", 2),
                ),
            ),
            let(
                "n_weighted_y",
                "sym.weighted_y",
                "weighted_y",
                BinaryExpr(
                    node_id=NodeId("n_weighted_y_expr"),
                    op="mul",
                    lhs=ref("n_ref_y_2", "sym.y", "y"),
                    rhs=literal("n_three", 3),
                ),
            ),
            let(
                "n_fused_sum",
                "sym.fused_sum",
                "fused_sum",
                BinaryExpr(
                    node_id=NodeId("n_fused_sum_expr"),
                    op="add",
                    lhs=ref("n_ref_weighted_x", "sym.weighted_x", "weighted_x"),
                    rhs=ref("n_ref_weighted_y", "sym.weighted_y", "weighted_y"),
                ),
            ),
            Return(
                node_id=NodeId("n_return_fused"),
                value=BinaryExpr(
                    node_id=NodeId("n_return_fused_expr"),
                    op="add",
                    lhs=ref("n_ref_fused_sum", "sym.fused_sum", "fused_sum"),
                    rhs=ref("n_ref_bias_2", "sym.bias", "bias"),
                ),
            ),
        ),
    )
    return program_module_from_kernels(
        transformed_kernel,
        entry="run",
        interpreter_id=NODE_KERNEL_INTERPRETER_ID,
        analyses={
            "demo.transform": {
                "schema": "htp.analysis.demo_transform.v1",
                "kernel": "affine_mix_fused",
                "rewrite": "weighted_affine",
            }
        },
        meta={"source": "examples/ir_program_module_flow/demo.py", "transform": "weighted_affine"},
    )


def render_stage_program(module: Any, destination: Path) -> Path:
    destination.write_text(render_program_module_payload(module.to_payload()), encoding="utf-8")
    return destination


def define_process_program() -> Any:
    affine_kernel = define_program().items.typed_items[0]
    if not isinstance(affine_kernel, Kernel):
        raise TypeError("expected first typed item to be a Kernel")
    affine_kernel_ref = item_ref("ref.item.affine_mix", affine_kernel.item_id.value, affine_kernel.name)
    tiles = channel(
        "item.channel.tiles",
        "tiles",
        channel_id="chan.tiles",
        dtype="f32",
        capacity=2,
    )
    partials = channel(
        "item.channel.partials",
        "partials",
        channel_id="chan.partials",
        dtype="f32",
        capacity=1,
    )
    pipeline = process_graph(
        "item.process.affine_pipeline",
        "affine_pipeline",
        channels=(tiles, partials),
        processes=(
            process(
                "node.process.dispatch",
                "dispatch",
                kernel=affine_kernel_ref,
                args=(ref("ref.proc.x", "sym.x", "x"), ref("ref.proc.y", "sym.y", "y")),
                steps=(
                    process_step("step.dispatch.pack", kind="compute", attrs={"op": "pack_tile"}),
                    process_step("step.dispatch.put", kind="put", channel_id="chan.tiles"),
                ),
                attrs={"role": "producer"},
            ),
            process(
                "node.process.combine",
                "combine",
                kernel=affine_kernel_ref,
                args=(ref("ref.proc.bias", "sym.bias", "bias"),),
                steps=(
                    process_step("step.combine.get", kind="get", channel_id="chan.tiles"),
                    process_step("step.combine.reduce", kind="compute", attrs={"op": "reduce_tile"}),
                    process_step("step.combine.put", kind="put", channel_id="chan.partials"),
                ),
                attrs={"role": "reducer"},
            ),
        ),
    )
    return program_module_from_items(
        affine_kernel,
        pipeline,
        entry="run",
        interpreter_id=NODE_PROCESS_GRAPH_INTERPRETER_ID,
        kernel_ir=KernelIR(entry=affine_kernel.name, args=(), buffers=(), ops=()),
        workload_ir=WorkloadIR(
            entry="run",
            tasks=(
                WorkloadTask(
                    task_id="dispatch",
                    kind="process",
                    kernel=affine_kernel.name,
                    args=("x", "y"),
                    entity_id="proc:dispatch",
                    attrs={"name": "dispatch", "role": "producer"},
                ),
                WorkloadTask(
                    task_id="combine",
                    kind="process",
                    kernel=affine_kernel.name,
                    args=("bias",),
                    entity_id="proc:combine",
                    attrs={"name": "combine", "role": "reducer"},
                ),
            ),
            channels=(
                {"name": "tiles", "dtype": "f32", "capacity": 2, "protocol": "fifo"},
                {"name": "partials", "dtype": "f32", "capacity": 1, "protocol": "fifo"},
            ),
            dependencies=(),
            processes=(
                {"name": "dispatch", "task_id": "dispatch", "kernel": affine_kernel.name},
                {"name": "combine", "task_id": "combine", "kernel": affine_kernel.name},
            ),
        ),
        analyses={
            "demo.process_graph": {
                "schema": "htp.analysis.demo_process_graph.v1",
                "graph": "affine_pipeline",
                "channels": ["tiles", "partials"],
            }
        },
        meta={"source": "examples/ir_program_module_flow/demo.py", "graph": "process"},
    )


def frontend_rule_demo() -> bool:
    spec = resolve_frontend(KernelSpec(name="affine_demo", args=(), ops=()))
    return bool(spec is not None and spec.rule is not None)


def run_demo() -> dict[str, Any]:
    base = define_program()
    base_result = base.run(3, 4, bias=5, scale=2)

    transformed = transform_program(base)
    transformed_result = transformed.run(3, 4, bias=5)
    process_module = define_process_program()
    process_result = process_module.run()

    with TemporaryDirectory() as tmpdir:
        program_path = render_stage_program(transformed, Path(tmpdir) / "program.py")
        rendered_program = program_path.read_text(encoding="utf-8")

    return {
        "base_result": base_result,
        "transformed_result": transformed_result,
        "base_typed_items": len(base.items.typed_items),
        "transformed_kernel": transformed.items.kernel_ir.entry,
        "rendered_has_program_module": "ProgramModule(" in rendered_program,
        "process_graph": process_result["graph"],
        "process_roles": [process["attrs"]["role"] for process in process_result["processes"]],
        "frontend_rule_demo": frontend_rule_demo(),
    }


if __name__ == "__main__":
    print(run_demo())
