from __future__ import annotations

import ctypes.util
import shutil
from pathlib import Path

import pytest

from examples.nvgpu_arknife_gemm.demo import compile_example as compile_nvgpu_example
from examples.nvgpu_arknife_gemm.demo import replay_latest_stage as replay_nvgpu_stage
from examples.nvgpu_arknife_gemm.demo import run_demo as run_nvgpu_demo
from examples.pto_pypto_vector_add.demo import compile_example as compile_pto_example
from examples.pto_pypto_vector_add.demo import replay_latest_stage as replay_pto_stage
from examples.pto_pypto_vector_add.demo import run_demo as run_pto_demo


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


@pytest.mark.skipif(
    shutil.which("g++") is None
    or (
        not Path("3rdparty/pto-runtime/python/runtime_builder.py").exists()
        and not Path("references/pto-runtime/python/runtime_builder.py").exists()
    ),
    reason="requires local pto-runtime reference checkout and host C++ toolchain",
)
def test_pto_example_runs_a2a3sim_end_to_end(tmp_path):
    summary = run_pto_demo(tmp_path / "pto_live")

    assert summary["build"]["ok"] is True
    assert summary["run"] is not None
    assert summary["run"]["ok"] is True
    assert summary["run"]["max_abs_error"] == 0.0


@pytest.mark.skipif(
    shutil.which("nvcc") is None or ctypes.util.find_library("cuda") is None,
    reason="requires nvcc and CUDA driver library for real-device execution",
)
def test_nvgpu_example_runs_real_device_path(tmp_path):
    summary = run_nvgpu_demo(tmp_path / "nvgpu_live")

    assert summary["device_build"]["ok"] is True
    assert summary["device_run"] is not None
    assert summary["device_run"]["ok"] is True
    assert summary["device_run"]["max_abs_error"] == 0.0
