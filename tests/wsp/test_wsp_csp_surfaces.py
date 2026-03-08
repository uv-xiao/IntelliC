from __future__ import annotations

from htp.csp import channel, process, program as csp_program
from htp.wsp import program as wsp_program
from htp.wsp import schedule as wsp_schedule
from htp.wsp import workload as wsp_workload


def _kernel() -> dict[str, object]:
    return {
        "name": "demo",
        "args": [{"name": "x", "kind": "buffer", "dtype": "f32", "shape": ["N"], "role": "input"}],
        "ops": [{"op": "broadcast", "source": "x", "out": "x", "shape": ["N"]}],
    }


def test_wsp_program_surface_is_plain_lowerable_data():
    payload = wsp_program(
        entry="demo",
        kernel=_kernel(),
        workload=wsp_workload(
            entry="demo",
            tasks=[{"task_id": "task0", "kind": "kernel_call", "kernel": "demo", "args": ["x"]}],
        ),
        schedule=wsp_schedule(resources={"num_warps": 2}),
        target={"backend": "generic", "option": "default"},
    )

    assert payload["wsp"]["schedule"]["resources"] == {"num_warps": 2}
    assert payload["kernel"]["name"] == "demo"


def test_csp_program_surface_carries_process_and_channel_metadata():
    payload = csp_program(
        entry="demo",
        kernel=_kernel(),
        channels=[channel("stream", dtype="f32", capacity=4)],
        processes=[process("worker", task_id="task0", kernel="demo", puts=[{"channel": "stream", "count": 1}])],
    )

    assert payload["csp"]["channels"] == [{"name": "stream", "dtype": "f32", "capacity": 4, "protocol": "fifo"}]
    assert payload["csp"]["processes"][0]["name"] == "worker"
