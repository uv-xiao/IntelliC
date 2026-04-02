from __future__ import annotations

from htp.ir.program import ProgramModule, compose_program_modules


def _module(
    *,
    source_surface: str,
    active_dialects: tuple[str, ...],
    workload_ir: dict[str, object],
) -> ProgramModule:
    return ProgramModule.from_program_dict(
        {
            "entry": "run",
            "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": "run"}},
            "kernel_ir": {
                "schema": "htp.kernel_ir.v1",
                "entry": "affine_mix",
                "args": [],
                "buffers": [],
                "ops": [],
            },
            "workload_ir": workload_ir,
            "meta": {
                "source_surface": source_surface,
                "active_dialects": list(active_dialects),
            },
        }
    )


def test_compose_program_modules_merges_typed_workload_records() -> None:
    wsp_module = _module(
        source_surface="htp.wsp.WSPProgramSpec",
        active_dialects=("htp.core", "htp.kernel", "htp.wsp"),
        workload_ir={
            "schema": "htp.workload_ir.v1",
            "entry": "run",
            "tasks": [
                {
                    "task_id": "load_tiles",
                    "kind": "kernel_call",
                    "kernel": "affine_mix",
                    "args": ["A", "B"],
                    "entity_id": "run:load_tiles",
                }
            ],
            "dependencies": [{"src": "load_tiles", "dst": "mma_tiles"}],
        },
    )
    csp_module = _module(
        source_surface="htp.csp.CSPProgramSpec",
        active_dialects=("htp.core", "htp.kernel", "htp.csp"),
        workload_ir={
            "schema": "htp.workload_ir.v1",
            "entry": "run",
            "tasks": [
                {
                    "task_id": "dispatch",
                    "kind": "process",
                    "kernel": "affine_mix",
                    "args": ["A"],
                    "entity_id": "run:dispatch",
                }
            ],
            "channels": [{"name": "tiles", "dtype": "f32", "capacity": 2, "protocol": "fifo"}],
            "processes": [
                {
                    "name": "dispatch",
                    "task_id": "dispatch",
                    "kernel": "affine_mix",
                    "args": ["A"],
                    "role": "producer",
                    "steps": [{"kind": "put", "channel": "tiles", "count": 1}],
                }
            ],
        },
    )

    composed = compose_program_modules(
        wsp_module,
        csp_module,
        canonical_program={"entry": "run", "wsp": {"entry": "run"}, "csp": {"entry": "run"}},
        source_surface="tests.compose",
        routine={"kind": "composed", "entry": "run"},
    )

    assert [task.task_id for task in composed.items.workload_ir.tasks] == ["load_tiles", "dispatch"]
    assert [(item.src, item.dst) for item in composed.items.workload_ir.dependencies] == [
        ("load_tiles", "mma_tiles")
    ]
    assert [channel.name for channel in composed.items.workload_ir.channels] == ["tiles"]
    assert [process.name for process in composed.items.workload_ir.processes] == ["dispatch"]
    assert composed.meta["active_dialects"] == ["htp.core", "htp.kernel", "htp.wsp", "htp.csp"]


def test_program_module_compose_classmethod_delegates() -> None:
    module = _module(
        source_surface="htp.kernel.KernelSpec",
        active_dialects=("htp.core", "htp.kernel"),
        workload_ir={"schema": "htp.workload_ir.v1", "entry": "run", "tasks": []},
    )

    composed = ProgramModule.compose(
        module,
        canonical_program={"entry": "run"},
        source_surface="tests.compose",
    )

    assert isinstance(composed, ProgramModule)
    assert composed.meta["source_surface"] == "tests.compose"
