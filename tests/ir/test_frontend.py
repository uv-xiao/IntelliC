from __future__ import annotations

from htp.ir.core.semantics import KernelIR, WorkloadTask
from htp.ir.frontends.shared import FrontendWorkload, build_frontend_program_module, kernel_spec_from_payload
from htp.ir.program.module import ProgramModule
from htp.kernel import KernelSpec


def test_shared_frontend_builder_reuses_kernel_module_semantics() -> None:
    kernel_spec = KernelSpec(
        name="vector_add",
        args=(),
        ops=(
            {
                "op_id": "op0",
                "op": "add",
                "inputs": ["lhs", "rhs"],
                "outputs": ["out"],
            },
        ),
    )
    kernel_module = kernel_spec.to_program_module()

    module = build_frontend_program_module(
        kernel_module=kernel_module,
        authored_program={
            "entry": "vector_add_pipeline",
            "kernel": kernel_spec.to_payload(),
            "workload": {"tasks": [{"task_id": "add0"}]},
        },
        workload=FrontendWorkload(
            entry="vector_add_pipeline",
            tasks=(
                WorkloadTask(
                    task_id="add0",
                    kind="kernel_call",
                    kernel="vector_add",
                    args=("lhs", "rhs", "out"),
                    entity_id="vector_add_pipeline:add0",
                ),
            ),
            routine={"kind": "routine", "entry": "vector_add_pipeline"},
        ),
        source_surface="htp.test.frontend",
        active_dialects=("htp.core", "htp.kernel", "htp.routine"),
    )

    assert isinstance(module, ProgramModule)
    assert isinstance(module.items.kernel_ir, KernelIR)
    assert module.items.kernel_ir.entry == kernel_module.items.kernel_ir.entry
    assert module.items.typed_items == kernel_module.items.typed_items
    assert module.items.workload_ir.entry == "vector_add_pipeline"
    assert module.items.workload_ir.tasks[0].task_id == "add0"
    assert module.meta["source_surface"] == "htp.test.frontend"
    assert module.meta["active_dialects"] == ["htp.core", "htp.kernel", "htp.routine"]
    assert module.meta["dialect_activation"]["requested"] == [
        "htp.core",
        "htp.kernel",
        "htp.routine",
    ]


def test_kernel_spec_from_payload_round_trips_public_kernel_shape() -> None:
    original = KernelSpec(
        name="affine_mix",
        args=(),
        ops=(
            {"op": "add", "inputs": ["lhs", "rhs"], "out": "tmp"},
            {"op": "mul", "inputs": ["tmp", "scale"], "out": "out"},
        ),
    )

    rebuilt = kernel_spec_from_payload(original.to_payload())

    assert isinstance(rebuilt, KernelSpec)
    assert rebuilt.to_payload() == original.to_payload()
