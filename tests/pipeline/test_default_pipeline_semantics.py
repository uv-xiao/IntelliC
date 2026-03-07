from htp.pipeline.defaults import run_default_pipeline


def test_default_pipeline_derives_nvgpu_semantics_and_schedule(tmp_path):
    package_dir = tmp_path / "out"

    result = run_default_pipeline(
        package_dir=package_dir,
        program={
            "entry": "demo_kernel",
            "ops": ["load", "mma", "store"],
            "analysis": {},
            "package": {"emitted": False},
            "target": {"backend": "nvgpu", "option": "ampere"},
        },
    )

    assert result.program["canonical_ast"] == {
        "entry": "demo_kernel",
        "target": {"backend": "nvgpu", "option": "ampere"},
        "kernel": {
            "name": "demo_kernel",
            "args": [
                {"name": "A", "kind": "buffer", "dtype": "f32", "shape": ["M", "K"], "role": "input"},
                {"name": "B", "kind": "buffer", "dtype": "f32", "shape": ["K", "N"], "role": "input"},
                {"name": "C", "kind": "buffer", "dtype": "f32", "shape": ["M", "N"], "role": "output"},
                {"name": "M", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "N", "kind": "scalar", "dtype": "i32", "role": "shape"},
                {"name": "K", "kind": "scalar", "dtype": "i32", "role": "shape"},
            ],
            "ops": [
                {
                    "op": "matmul",
                    "lhs": "A",
                    "rhs": "B",
                    "out": "C",
                    "m": "M",
                    "n": "N",
                    "k": "K",
                    "dtype": "f32",
                }
            ],
        },
        "workload": {
            "entry": "demo_kernel",
            "tasks": [
                {
                    "task_id": "task0",
                    "kind": "kernel_call",
                    "kernel": "demo_kernel",
                    "args": ["A", "B", "C", "M", "N", "K"],
                }
            ],
            "channels": [],
            "dependencies": [],
        },
    }
    assert result.program["kernel_ir"]["ops"] == [
        {
            "op_id": "op0",
            "entity_id": "demo_kernel:E6",
            "op": "matmul",
            "inputs": ["A", "B"],
            "outputs": ["C"],
            "attrs": {"dtype": "f32", "m": "M", "n": "N", "k": "K"},
            "effects": {"reads": ["A", "B"], "writes": ["C"]},
        }
    ]
    assert result.program["layout"] == {
        "schema": "htp.layout.v1",
        "target": {"backend": "nvgpu", "option": "ampere"},
        "memory_spaces": {"A": "global", "B": "global", "C": "global"},
        "threading": {"thread_block": [16, 16, 1], "warp_group": 1},
        "tiling": {"block": [16, 16, 16], "pipeline_stages": 1, "backend": "nvgpu"},
    }
    assert result.program["effects"] == {
        "schema": "htp.effects.v1",
        "reads": {"op0": ["A", "B"]},
        "writes": {"op0": ["C"]},
        "barriers": [],
        "channels": [],
    }
    assert result.program["schedule"]["ordered_ops"] == ["op0"]
    assert result.program["package"] == {
        "emitted": True,
        "entry": "demo_kernel",
        "entrypoint": "demo_kernel",
        "kernel_entry": "demo_kernel",
        "target_backend": "nvgpu",
        "scheduled_tick_count": 1,
        "has_barrier": False,
    }
