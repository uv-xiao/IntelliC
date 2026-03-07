from htp.pipeline.defaults import run_default_pipeline


def test_default_pipeline_derives_nvgpu_layout_and_schedule(tmp_path):
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

    assert result.program["canonical_ast"]["ops"] == [
        {
            "op_id": "op0",
            "op": "load",
            "phase": "producer",
            "reads": ["input"],
            "writes": ["tile"],
            "latency": 1,
            "barrier_after": True,
        },
        {
            "op_id": "op1",
            "op": "mma",
            "phase": "compute",
            "reads": ["tile", "weights"],
            "writes": ["accum"],
            "latency": 2,
            "barrier_after": False,
        },
        {
            "op_id": "op2",
            "op": "store",
            "phase": "consumer",
            "reads": ["accum"],
            "writes": ["output"],
            "latency": 1,
            "barrier_after": False,
        },
    ]
    assert result.program["layout"] == {
        "target": {"backend": "nvgpu", "option": "ampere"},
        "tile_shape": [16, 16],
        "memory_spaces": {
            "input": "global",
            "tile": "shared",
            "accum": "register",
            "output": "global",
        },
        "threading": {
            "thread_block": [128, 1, 1],
            "warp_group": 1,
        },
    }
    assert result.program["schedule"]["ordered_ops"] == ["op0", "op0.barrier", "op1", "op2"]
    assert result.program["package"] == {
        "emitted": True,
        "entry": "demo_kernel",
        "entrypoint": "demo_kernel",
        "target_backend": "nvgpu",
        "scheduled_tick_count": 4,
        "has_barrier": True,
    }
