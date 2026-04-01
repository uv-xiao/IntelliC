from __future__ import annotations

from htp.ir.core.nodes import (
    BinaryExpr,
    ForStmt,
    Kernel,
    NodeId,
    ProcessGraph,
    Return,
    SendStmt,
    TaskGraph,
    channel,
    dependency,
    from_payload,
    item_ref,
    kernel,
    let,
    param,
    process,
    process_graph,
    process_step,
    ref,
    region,
    task,
    task_graph,
    to_payload,
)
from htp.ir.core.semantics import KernelIR, WorkloadIR, WorkloadTask
from htp.ir.interpreters.entrypoints import (
    NODE_KERNEL_INTERPRETER_ID,
    NODE_PROCESS_GRAPH_INTERPRETER_ID,
    NODE_TASK_GRAPH_INTERPRETER_ID,
)
from htp.ir.program.build import (
    build_tile_streamed_gemm_core_module,
    program_module_from_items,
    program_module_from_kernels,
)


def test_kernel_node_payload_round_trip() -> None:
    item = _demo_kernel()

    payload = to_payload(item)
    rebuilt = from_payload(payload)

    assert rebuilt == item


def test_task_graph_payload_round_trip() -> None:
    graph = _demo_task_graph()

    payload = to_payload(graph)
    rebuilt = from_payload(payload)

    assert rebuilt == graph


def test_process_graph_payload_round_trip() -> None:
    graph = _demo_process_graph()

    payload = to_payload(graph)
    rebuilt = from_payload(payload)

    assert rebuilt == graph


def test_kernel_node_interpreter_runs_program_module() -> None:
    module = program_module_from_kernels(_demo_kernel(), interpreter_id=NODE_KERNEL_INTERPRETER_ID)

    assert module.run(3, 4, bias=5, scale=2) == 24


def test_task_graph_interpreter_runs_typed_graph_module() -> None:
    task_item = _demo_task_graph()
    kernel_item = _demo_kernel()
    module = program_module_from_items(
        kernel_item,
        task_item,
        entry="run",
        interpreter_id=NODE_TASK_GRAPH_INTERPRETER_ID,
        kernel_ir=KernelIR(entry=kernel_item.name, args=(), buffers=(), ops=()),
        workload_ir=WorkloadIR(
            entry="run",
            tasks=(
                WorkloadTask(
                    task_id="load_tiles",
                    kind="kernel_call",
                    kernel="affine_mix",
                    args=("x", "y", "bias", "scale"),
                    entity_id="graph:load_tiles",
                ),
                WorkloadTask(
                    task_id="mma_tiles",
                    kind="kernel_call",
                    kernel="affine_mix",
                    args=("x", "y", "bias", "scale"),
                    entity_id="graph:mma_tiles",
                ),
            ),
            channels=(),
            dependencies=({"src": "load_tiles", "dst": "mma_tiles"},),
        ),
    )

    execution = module.run()

    assert execution["graph"] == "affine_mainloop"
    assert [task["task_id"] for task in execution["tasks"]] == ["load_tiles", "mma_tiles"]
    assert execution["dependencies"] == [{"src": "load_tiles", "dst": "mma_tiles"}]


def test_process_graph_interpreter_runs_typed_process_module() -> None:
    process_item = _demo_process_graph()
    kernel_item = _demo_kernel()
    module = program_module_from_items(
        kernel_item,
        process_item,
        entry="run",
        interpreter_id=NODE_PROCESS_GRAPH_INTERPRETER_ID,
        kernel_ir=KernelIR(entry=kernel_item.name, args=(), buffers=(), ops=()),
        workload_ir=WorkloadIR(
            entry="run",
            tasks=(
                WorkloadTask(
                    task_id="dispatch",
                    kind="process",
                    kernel="affine_mix",
                    args=("x", "y", "bias", "scale"),
                    entity_id="proc:dispatch",
                ),
            ),
            channels=({"name": "tiles", "dtype": "f32", "capacity": 2, "protocol": "fifo"},),
            dependencies=(),
            processes=(
                {
                    "name": "dispatch",
                    "task_id": "dispatch",
                    "kernel": "affine_mix",
                    "steps": [{"kind": "put", "channel": "tiles"}],
                },
            ),
        ),
    )

    execution = module.run()

    assert execution["graph"] == "tile_pipeline"
    assert execution["channels"][0]["name"] == "tiles"
    assert execution["processes"][0]["steps"] == [
        {"kind": "put", "attrs": {"tile": "A"}, "channel_id": "chan.tiles"}
    ]


def test_typed_nodes_cover_kernel_task_and_process_regions() -> None:
    module = build_tile_streamed_gemm_core_module()

    assert isinstance(module.items.typed_items[0], Kernel)
    assert isinstance(module.items.typed_items[1], TaskGraph)
    assert isinstance(module.items.typed_items[2], ProcessGraph)
    assert any(isinstance(statement, ForStmt) for statement in module.items.typed_items[0].body.statements)
    assert module.items.typed_items[2].body is not None
    assert any(isinstance(statement, SendStmt) for statement in module.items.typed_items[2].body.statements)


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


def _demo_task_graph() -> TaskGraph:
    kernel_handle = item_ref("ref.item.affine_mix", "item.affine_mix", "affine_mix")
    return task_graph(
        "item.affine_mainloop",
        "affine_mainloop",
        tasks=(
            task(
                "node.task.load_tiles",
                "load_tiles",
                kernel=kernel_handle,
                args=(ref("ref.arg.x", "sym.x", "x"), ref("ref.arg.y", "sym.y", "y")),
                attrs={"role": "producer"},
            ),
            task(
                "node.task.mma_tiles",
                "mma_tiles",
                kernel=kernel_handle,
                args=(ref("ref.arg.bias", "sym.bias", "bias"), ref("ref.arg.scale", "sym.scale", "scale")),
                attrs={"role": "consumer"},
            ),
        ),
        dependencies=(dependency("dep.load_to_mma", src_task="load_tiles", dst_task="mma_tiles"),),
    )


def _demo_process_graph() -> ProcessGraph:
    kernel_handle = item_ref("ref.item.affine_mix.proc", "item.affine_mix", "affine_mix")
    tiles = channel(
        "item.channel.tiles",
        "tiles",
        channel_id="chan.tiles",
        dtype="f32",
        capacity=2,
        protocol="fifo",
    )
    return process_graph(
        "item.tile_pipeline",
        "tile_pipeline",
        channels=(tiles,),
        processes=(
            process(
                "node.process.dispatch",
                "dispatch",
                kernel=kernel_handle,
                args=(ref("ref.proc.x", "sym.x", "x"),),
                steps=(
                    process_step(
                        "step.dispatch.put", kind="put", channel_id="chan.tiles", attrs={"tile": "A"}
                    ),
                ),
                attrs={"role": "producer"},
            ),
        ),
    )
