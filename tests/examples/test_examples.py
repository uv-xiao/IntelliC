from __future__ import annotations

from pathlib import Path

from examples.nvgpu_arknife_gemm.demo import compile_example as compile_nvgpu_example
from examples.nvgpu_arknife_gemm.demo import replay_latest_stage as replay_nvgpu_stage
from examples.pto_pypto_vector_add.demo import compile_example as compile_pto_example
from examples.pto_pypto_vector_add.demo import replay_latest_stage as replay_pto_stage


def test_pto_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "pto_example"
    compile_summary = compile_pto_example(package_dir)
    replay_summary = replay_pto_stage(package_dir)

    assert compile_summary["target"] == {"backend": "pto", "option": "a2a3sim"}
    assert (Path(compile_summary["manifest_path"])).is_file()
    assert replay_summary["ok"] is True
    assert replay_summary["stage_id"].startswith("s")


def test_nvgpu_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "nvgpu_example"
    compile_summary = compile_nvgpu_example(package_dir)
    replay_summary = replay_nvgpu_stage(package_dir)

    assert compile_summary["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert (Path(compile_summary["manifest_path"])).is_file()
    assert replay_summary["ok"] is True
    assert replay_summary["stage_id"].startswith("s")
