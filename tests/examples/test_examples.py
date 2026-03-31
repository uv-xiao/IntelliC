from __future__ import annotations

import ctypes.util
import shutil
from pathlib import Path

import pytest

from examples.aie_channel_pipeline.demo import compile_example as compile_aie_example
from examples.aie_channel_pipeline.demo import replay_latest_stage as replay_aie_stage
from examples.csp_channel_pipeline.demo import compile_example as compile_csp_example
from examples.csp_channel_pipeline.demo import replay_latest_stage as replay_csp_stage
from examples.extensions.cpu_ref_vector_add.demo import compile_example as compile_cpu_ref_example
from examples.extensions.cpu_ref_vector_add.demo import replay_latest_stage as replay_cpu_ref_stage
from examples.extensions.cpu_ref_vector_add.demo import run_demo as run_cpu_ref_demo
from examples.ir_program_module_flow.demo import run_demo as run_ir_program_module_demo
from examples.mlir_cse_extension.demo import compile_example as compile_mlir_cse_example
from examples.mlir_cse_extension.demo import replay_latest_stage as replay_mlir_cse_stage
from examples.nvgpu_arknife_blackwell.demo import compile_example as compile_nvgpu_blackwell_example
from examples.nvgpu_arknife_blackwell.demo import replay_latest_stage as replay_nvgpu_blackwell_stage
from examples.nvgpu_arknife_gemm.demo import compile_example as compile_nvgpu_example
from examples.nvgpu_arknife_gemm.demo import replay_latest_stage as replay_nvgpu_stage
from examples.nvgpu_arknife_gemm.demo import run_demo as run_nvgpu_demo
from examples.pto_pypto_gelu.demo import compile_example as compile_pto_gelu_example
from examples.pto_pypto_gelu.demo import replay_latest_stage as replay_pto_gelu_stage
from examples.pto_pypto_gelu.demo import run_demo as run_pto_gelu_demo
from examples.pto_pypto_swiglu.demo import compile_example as compile_pto_swiglu_example
from examples.pto_pypto_swiglu.demo import replay_latest_stage as replay_pto_swiglu_stage
from examples.pto_pypto_swiglu.demo import run_demo as run_pto_swiglu_demo
from examples.pto_pypto_vector_add.demo import compile_example as compile_pto_example
from examples.pto_pypto_vector_add.demo import replay_latest_stage as replay_pto_stage
from examples.pto_pypto_vector_add.demo import run_demo as run_pto_demo
from examples.pto_pypto_vector_dag.demo import compile_example as compile_pto_vector_dag_example
from examples.pto_pypto_vector_dag.demo import replay_latest_stage as replay_pto_vector_dag_stage
from examples.pto_pypto_vector_dag.demo import run_demo as run_pto_vector_dag_demo
from examples.serving_routine.demo import compile_example as compile_serving_example
from examples.serving_routine.demo import replay_latest_stage as replay_serving_stage
from examples.wsp_littlekernel_pipelined_gemm.demo import compile_example as compile_littlekernel_example
from examples.wsp_littlekernel_pipelined_gemm.demo import replay_latest_stage as replay_littlekernel_stage
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
    assert [item["instruction"] for item in compile_summary["instruction_plan"]] == [
        "cp_async",
        "cp_async",
        "ldmatrix",
        "ldmatrix",
        "mma_sync",
        "commit",
    ]
    assert replay_summary["ok"] is True
    assert replay_summary["stage_id"].startswith("s")


def test_nvgpu_blackwell_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "nvgpu_blackwell_example"
    compile_summary = compile_nvgpu_blackwell_example(package_dir)
    replay_summary = replay_nvgpu_blackwell_stage(package_dir)

    assert compile_summary["target"] == {"backend": "nvgpu", "option": "blackwell"}
    assert compile_summary["hardware"]["profile"] == "blackwell"
    assert [item["instruction"] for item in compile_summary["instruction_plan"]] == [
        "tma_load",
        "tma_load",
        "wgmma",
        "tma_store",
    ]
    assert replay_summary["ok"] is True
    assert replay_summary["stage_id"].startswith("s")


def test_pto_swiglu_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "pto_swiglu_example"
    compile_summary = compile_pto_swiglu_example(package_dir)
    replay_summary = replay_pto_swiglu_stage(package_dir)

    assert compile_summary["target"] == {"backend": "pto", "option": "a2a3sim"}
    assert (Path(compile_summary["manifest_path"])).is_file()
    assert replay_summary["ok"] is True
    assert replay_summary["stage_id"].startswith("s")


def test_pto_gelu_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "pto_gelu_example"
    compile_summary = compile_pto_gelu_example(package_dir)
    replay_summary = replay_pto_gelu_stage(package_dir)

    assert compile_summary["target"] == {"backend": "pto", "option": "a2a3sim"}
    assert (Path(compile_summary["manifest_path"])).is_file()
    assert replay_summary["ok"] is True
    assert replay_summary["stage_id"].startswith("s")


def test_pto_vector_dag_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "pto_vector_dag_example"
    compile_summary = compile_pto_vector_dag_example(package_dir)
    replay_summary = replay_pto_vector_dag_stage(package_dir)

    assert compile_summary["target"] == {"backend": "pto", "option": "a2a3sim"}
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
    assert [task["task_id"] for task in replay_summary["workload_ir"]["tasks"]] == [
        "load_tiles",
        "mma_tiles",
        "accumulate_tiles",
        "store_tiles",
    ]
    assert replay_summary["workload_ir"]["tasks"][0]["attrs"]["role"] == "producer"
    assert replay_summary["workload_ir"]["tasks"][1]["attrs"]["role"] == "consumer"
    assert replay_summary["workload_ir"]["tasks"][2]["attrs"]["role"] == "reducer"
    assert replay_summary["workload_ir"]["dependencies"] == [
        {"src": "load_tiles", "dst": "mma_tiles"},
        {"src": "mma_tiles", "dst": "accumulate_tiles"},
        {"src": "accumulate_tiles", "dst": "store_tiles"},
    ]
    assert replay_summary["workload_ir"]["tasks"][0]["args"] == ["A", "B", "C", "M", "N", "K"]
    assert replay_summary["workload_ir"]["tasks"][0]["attrs"]["stages"][0]["steps"] == [
        {"kind": "step", "op": "cp_async", "source": "A", "target": "a_tile"},
        {"kind": "step", "op": "cp_async", "source": "B", "target": "b_tile"},
    ]
    assert replay_summary["workload_ir"]["tasks"][2]["attrs"]["stages"][0]["steps"] == [
        {"kind": "step", "op": "reduce_accumulators", "source": "acc"},
        {"kind": "step", "op": "apply_epilogue", "target": "C"},
    ]
    assert replay_summary["kernel_ir"]["ops"][0]["op"] == "slice"
    assert replay_summary["kernel_ir"]["ops"][0]["attrs"]["offset_exprs"] == ["0", "warp_stage * 16"]
    assert replay_summary["kernel_ir"]["ops"][0]["attrs"]["regions"][0]["modifier"] == "unroll"
    assert replay_summary["kernel_ir"]["ops"][2]["attrs"]["regions"][1]["kind"] == "warp_tile"


def test_littlekernel_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "littlekernel_example"
    compile_summary = compile_littlekernel_example(package_dir)
    replay_summary = replay_littlekernel_stage(package_dir)

    assert compile_summary["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert replay_summary["ok"] is True
    assert replay_summary["schedule"]["pipeline_depth"] >= 3
    assert replay_summary["schedule"]["launch"]["num_warps"] == 8
    assert [task["task_id"] for task in replay_summary["workload_ir"]["tasks"]] == [
        "prefetch_tiles",
        "steady_tiles",
        "epilogue_tiles",
        "writeback_tiles",
    ]
    assert replay_summary["workload_ir"]["tasks"][0]["args"] == ["A", "B", "C", "M", "N", "K"]
    assert replay_summary["workload_ir"]["tasks"][1]["attrs"]["stages"][0] == {
        "name": "prologue",
        "steps": [
            {"kind": "step", "op": "ldmatrix", "source": "a_stage"},
            {"kind": "step", "op": "ldmatrix", "source": "b_stage"},
        ],
    }
    assert replay_summary["workload_ir"]["tasks"][1]["attrs"]["stages"][1] == {
        "name": "steady",
        "steps": [
            {"kind": "step", "op": "mma_sync", "stage": 0},
            {"kind": "step", "op": "mma_sync", "stage": 1},
            {"kind": "step", "op": "advance_pipeline"},
        ],
    }
    assert replay_summary["workload_ir"]["tasks"][2]["attrs"]["stages"][0] == {
        "name": "epilogue",
        "steps": [
            {"kind": "step", "op": "reduce_accumulators", "source": "acc"},
            {"kind": "step", "op": "convert_output", "target": "C"},
        ],
    }
    assert replay_summary["kernel_ir"]["ops"][0]["op"] == "slice"
    assert replay_summary["kernel_ir"]["ops"][0]["attrs"]["offset_exprs"] == ["0", "stage * 16"]
    assert replay_summary["kernel_ir"]["ops"][0]["attrs"]["regions"][0]["modifier"] == "unroll"
    assert replay_summary["kernel_ir"]["ops"][2]["attrs"]["regions"][1]["kind"] == "mainloop_stage"


def test_csp_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "csp_example"
    compile_summary = compile_csp_example(package_dir)
    replay_summary = replay_csp_stage(package_dir)

    assert compile_summary["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert replay_summary["ok"] is True
    assert [process["name"] for process in replay_summary["workload_ir"]["processes"]] == [
        "dispatch_tiles",
        "combine_tiles",
        "finalize_rows",
        "writeback_tiles",
    ]
    assert replay_summary["workload_ir"]["processes"][0]["args"] == ["A", "B", "C", "M", "N", "K"]
    assert replay_summary["workload_ir"]["processes"][0]["role"] == "producer"
    assert replay_summary["workload_ir"]["processes"][0]["steps"][0] == {
        "kind": "compute",
        "op": "pack_tile",
        "source": "A",
    }
    assert replay_summary["workload_ir"]["processes"][1]["steps"][1] == {
        "kind": "compute",
        "op": "reduce_partials",
        "channel": "tiles",
    }
    assert replay_summary["workload_ir"]["processes"][2]["steps"][1] == {
        "kind": "compute",
        "op": "normalize_rows",
        "channel": "partials",
    }
    assert replay_summary["effects"]["protocols"] == [
        {
            "channel": "tiles",
            "protocol": "fifo",
            "capacity": 2,
            "puts": 1,
            "gets": 1,
            "balanced": True,
            "participants": ["combine_tiles", "dispatch_tiles"],
            "hazards": [],
            "deadlock_safe": True,
        },
        {
            "channel": "partials",
            "protocol": "fifo",
            "capacity": 1,
            "puts": 1,
            "gets": 1,
            "balanced": True,
            "participants": ["combine_tiles", "finalize_rows"],
            "hazards": [],
            "deadlock_safe": True,
        },
        {
            "channel": "ready_rows",
            "protocol": "fifo",
            "capacity": 1,
            "puts": 1,
            "gets": 1,
            "balanced": True,
            "participants": ["finalize_rows", "writeback_tiles"],
            "hazards": [],
            "deadlock_safe": True,
        },
    ]


def test_ir_program_module_example_defines_executes_and_transforms():
    summary = run_ir_program_module_demo()

    assert summary == {
        "base_result": 24,
        "transformed_result": 23,
        "base_typed_items": 1,
        "transformed_kernel": "affine_mix_fused",
        "rendered_has_program_module": True,
        "process_graph": "affine_pipeline",
        "process_roles": ["producer", "reducer"],
        "frontend_rule_demo": True,
    }


def test_ir_program_module_example_reports_frontend_rule_proof() -> None:
    summary = run_ir_program_module_demo()

    assert summary["frontend_rule_demo"] is True


def test_aie_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "aie_example"
    compile_summary = compile_aie_example(package_dir)
    replay_summary = replay_aie_stage(package_dir)

    assert compile_summary["target"] == {"backend": "aie", "option": "xdna2-npu1"}
    assert replay_summary["ok"] is True
    assert replay_summary["analysis_inventory"] == [
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


def test_cpu_ref_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "cpu_ref_example"
    compile_summary = compile_cpu_ref_example(package_dir)
    replay_summary = replay_cpu_ref_stage(package_dir)
    run_summary = run_cpu_ref_demo(package_dir)["run"]

    assert compile_summary["target"] == {"backend": "cpu_ref", "option": None}
    assert replay_summary["ok"] is True
    assert run_summary["ok"] is True
    assert run_summary["max_abs_error"] == 0.0


def test_mlir_cse_extension_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "mlir_cse_example"
    compile_summary = compile_mlir_cse_example(package_dir)
    replay_summary = replay_mlir_cse_stage(package_dir)

    assert compile_summary["solver"]["ok"] is True
    assert compile_summary["solver"]["template_id"] == "htp.default+htp_ext.mlir_cse.v1"
    assert compile_summary["solver"]["extension_results"]["htp_ext.mlir_cse"]["eligible"] is True
    assert replay_summary["ok"] is True
    assert replay_summary["result"] == {"entry": "expr_demo", "result": 33, "rewrites": []}
    assert "mlir_cse" in replay_summary["extensions"]


def test_serving_routine_example_compiles_and_replays(tmp_path):
    package_dir = tmp_path / "serving_example"
    compile_summary = compile_serving_example(package_dir)
    replay_summary = replay_serving_stage(package_dir)

    assert compile_summary["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert replay_summary["ok"] is True
    assert [task["task_id"] for task in replay_summary["workload_ir"]["tasks"]] == [
        "prefill",
        "decode_step_0",
        "decode_step_1",
        "sample",
        "writeback",
    ]
    assert replay_summary["workload_ir"]["routine"]["kind"] == "serving_routine"
    assert replay_summary["workload_ir"]["routine"]["phases"][0]["name"] == "prefill"
    assert replay_summary["workload_ir"]["routine"]["phases"][1]["name"] == "decode"
    assert replay_summary["workload_ir"]["routine"]["state_edges"][0] == {
        "src": "kv_fill",
        "dst": "token_step_0",
        "via": "decode_step_0",
    }
    assert [channel["name"] for channel in replay_summary["workload_ir"]["channels"]] == [
        "token_batches",
        "decoded_batches",
    ]
    assert replay_summary["workload_ir"]["dependencies"] == [
        {"src": "prefill", "dst": "decode_step_0"},
        {"src": "decode_step_0", "dst": "decode_step_1"},
        {"src": "decode_step_1", "dst": "sample"},
        {"src": "sample", "dst": "writeback"},
    ]


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
    shutil.which("g++") is None
    or (
        not Path("3rdparty/pto-runtime/python/runtime_builder.py").exists()
        and not Path("references/pto-runtime/python/runtime_builder.py").exists()
    ),
    reason="requires local pto-runtime reference checkout and host C++ toolchain",
)
def test_pto_swiglu_example_runs_a2a3sim_end_to_end(tmp_path):
    summary = run_pto_swiglu_demo(tmp_path / "pto_swiglu_live")

    assert summary["build"]["ok"] is True
    assert summary["run"] is not None
    assert summary["run"]["ok"] is True
    assert summary["run"]["max_abs_error"] < 1e-6


@pytest.mark.skipif(
    shutil.which("g++") is None
    or (
        not Path("3rdparty/pto-runtime/python/runtime_builder.py").exists()
        and not Path("references/pto-runtime/python/runtime_builder.py").exists()
    ),
    reason="requires local pto-runtime reference checkout and host C++ toolchain",
)
def test_pto_gelu_example_runs_a2a3sim_end_to_end(tmp_path):
    summary = run_pto_gelu_demo(tmp_path / "pto_gelu_live")

    assert summary["build"]["ok"] is True
    assert summary["run"] is not None
    assert summary["run"]["ok"] is True
    assert summary["run"]["max_abs_error"] < 1e-6


@pytest.mark.skipif(
    shutil.which("g++") is None
    or (
        not Path("3rdparty/pto-runtime/python/runtime_builder.py").exists()
        and not Path("references/pto-runtime/python/runtime_builder.py").exists()
    ),
    reason="requires local pto-runtime reference checkout and host C++ toolchain",
)
def test_pto_vector_dag_example_runs_a2a3sim_end_to_end(tmp_path):
    summary = run_pto_vector_dag_demo(tmp_path / "pto_vector_dag_live")

    assert summary["build"]["ok"] is True
    assert summary["run"] is not None
    assert summary["run"]["ok"] is True
    assert summary["run"]["max_abs_error"] < 1e-6


@pytest.mark.skipif(
    shutil.which("g++") is None
    or (
        not Path("3rdparty/pto-runtime/python/runtime_builder.py").exists()
        and not Path("references/pto-runtime/python/runtime_builder.py").exists()
    ),
    reason="requires local pto-runtime reference checkout and host C++ toolchain",
)
def test_pto_examples_run_sequentially_in_one_process(tmp_path):
    first = run_pto_demo(tmp_path / "pto_vector_add_live")
    second = run_pto_swiglu_demo(tmp_path / "pto_swiglu_live")
    third = run_pto_gelu_demo(tmp_path / "pto_gelu_live")
    fourth = run_pto_vector_dag_demo(tmp_path / "pto_vector_dag_live")

    assert first["run"] is not None
    assert first["run"]["ok"] is True
    assert second["run"] is not None
    assert second["run"]["ok"] is True
    assert second["run"]["max_abs_error"] < 1e-6
    assert third["run"] is not None
    assert third["run"]["ok"] is True
    assert third["run"]["max_abs_error"] < 1e-6
    assert fourth["run"] is not None
    assert fourth["run"]["ok"] is True
    assert fourth["run"]["max_abs_error"] < 1e-6


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
