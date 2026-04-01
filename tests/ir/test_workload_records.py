from __future__ import annotations

from htp.ir.core.semantics import (
    WorkloadChannel,
    WorkloadDependency,
    WorkloadIR,
    WorkloadProcess,
    WorkloadProcessStep,
    WorkloadTask,
    workload_ir_from_payload,
    workload_ir_payload,
)


def test_workload_ir_round_trips_typed_records() -> None:
    workload = WorkloadIR(
        entry="tile_pipeline",
        tasks=(
            WorkloadTask(
                task_id="dispatch",
                kind="process",
                kernel="tile_kernel",
                args=("A", "B"),
                entity_id="tile_pipeline:dispatch",
                attrs={"role": "producer"},
            ),
        ),
        channels=(
            WorkloadChannel(name="tiles", dtype="f32", capacity=2, protocol="fifo"),
        ),
        dependencies=(WorkloadDependency(src="dispatch", dst="combine"),),
        processes=(
            WorkloadProcess(
                name="dispatch",
                task_id="dispatch",
                kernel="tile_kernel",
                args=("A", "B"),
                role="producer",
                steps=(
                    WorkloadProcessStep(kind="compute", attrs={"name": "pack_tile"}),
                    WorkloadProcessStep(kind="put", attrs={"channel": "tiles", "count": 1}),
                ),
            ),
        ),
        routine={"kind": "csp", "entry": "tile_pipeline"},
    )

    payload = workload_ir_payload(workload)
    rebuilt = workload_ir_from_payload(payload)

    assert rebuilt == workload
    assert payload["channels"] == [
        {"name": "tiles", "dtype": "f32", "capacity": 2, "protocol": "fifo"}
    ]
    assert payload["dependencies"] == [{"src": "dispatch", "dst": "combine"}]
    assert payload["processes"][0]["steps"] == [
        {"kind": "compute", "name": "pack_tile"},
        {"kind": "put", "channel": "tiles", "count": 1},
    ]
