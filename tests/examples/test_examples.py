from __future__ import annotations

import ctypes.util
import shutil
from pathlib import Path

import pytest

from examples.aie_channel_pipeline.demo import compile_example as compile_aie_example
from examples.aie_channel_pipeline.demo import replay_latest_stage as replay_aie_stage
from examples.csp_channel_pipeline.demo import compile_example as compile_csp_example
from examples.csp_channel_pipeline.demo import replay_latest_stage as replay_csp_stage
from examples.nvgpu_arknife_gemm.demo import compile_example as compile_nvgpu_example
from examples.nvgpu_arknife_gemm.demo import replay_latest_stage as replay_nvgpu_stage
from examples.nvgpu_arknife_gemm.demo import run_demo as run_nvgpu_demo
from examples.pto_pypto_vector_add.demo import compile_example as compile_pto_example
from examples.pto_pypto_vector_add.demo import replay_latest_stage as replay_pto_stage
from examples.pto_pypto_vector_add.demo import run_demo as run_pto_demo
from examples.wsp_warp_gemm.demo import compile_example as compile_wsp_example
from examples.wsp_warp_gemm.demo import replay_latest_stage as replay_wsp_stage


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


def test_wsp_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "wsp_example"
    compile_summary = compile_wsp_example(package_dir)
    replay_summary = replay_wsp_stage(package_dir)

    assert compile_summary["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert replay_summary["ok"] is True
    assert replay_summary["schedule"]["pipeline_depth"] >= 1
    assert replay_summary["schedule"]["launch"]["num_warps"] == 4


def test_csp_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "csp_example"
    compile_summary = compile_csp_example(package_dir)
    replay_summary = replay_csp_stage(package_dir)

    assert compile_summary["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert replay_summary["ok"] is True
    assert replay_summary["effects"]["protocols"] == [
        {
            "channel": "tiles",
            "protocol": "fifo",
            "capacity": 2,
            "puts": 1,
            "gets": 1,
            "balanced": True,
        }
    ]


def test_aie_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "aie_example"
    compile_summary = compile_aie_example(package_dir)
    replay_summary = replay_aie_stage(package_dir)

    assert compile_summary["target"] == {"backend": "aie", "option": "xdna2-npu1"}
    assert replay_summary["ok"] is True
    assert replay_summary["analysis_index"]["analyses"] == [
        {
            "analysis_id": "htp_ext.aie::MappingPlan@1",
            "schema": "htp.analysis.aie_mapping_plan.v1",
            "path": f"ir/stages/{replay_summary['stage_id']}/analysis/aie_mapping_plan.json",
        },
        {
            "analysis_id": "htp_ext.aie::FIFOPlan@1",
            "schema": "htp.analysis.aie_fifo_plan.v1",
            "path": f"ir/stages/{replay_summary['stage_id']}/analysis/aie_fifo_plan.json",
        },
    ]
    assert [tile["task_id"] for tile in replay_summary["mapping"]["tiles"]] == ["p0", "p1"]
    assert replay_summary["fifos"]["channels"][0]["name"] == "tiles"


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
