from __future__ import annotations

import pytest

import htp
from htp import ark
from htp.csp import program as csp_program
from htp.kernel import (
    KernelValue,
    async_copy,
    barrier,
    broadcast,
    buffer,
    cast,
    channel_recv,
    channel_send,
    elementwise_add,
    kernel,
    matmul,
    mma,
    reduction_sum,
    scalar,
    sigmoid,
    store,
    transpose,
    value,
)
from htp.routine import call, fifo_channel, program
from htp.wsp import program as wsp_program


def test_compile_program_accepts_public_program_surface(tmp_path):
    package_dir = tmp_path / "surface_pkg"

    @kernel
    def vector_add(
        lhs: buffer(dtype="f32", shape=("size",), role="input"),
        rhs: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        elementwise_add(lhs, rhs, out=out, shape=(size,), dtype="f32")

    compiled = htp.compile_program(package_dir=package_dir, target="pto-a2a3sim", program=vector_add)

    assert compiled.manifest["inputs"]["entry"] == "vector_add"
    assert compiled.manifest["target"]["backend"] == "pto"


def test_compile_program_accepts_expression_first_kernel_surface(tmp_path):
    package_dir = tmp_path / "expression_surface_pkg"

    @kernel
    def vector_add(
        lhs: buffer(dtype="f32", shape=("size",), role="input"),
        rhs: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, lhs + rhs)

    compiled = htp.compile_program(package_dir=package_dir, target="pto-a2a3sim", program=vector_add)

    assert compiled.manifest["inputs"]["entry"] == "vector_add"
    assert compiled.manifest["target"]["backend"] == "pto"


def test_expression_first_kernel_surface_supports_fused_temporaries(tmp_path):
    @kernel
    def swiglu(
        gate: buffer(dtype="f32", shape=("size",), role="input"),
        up: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        gate_sigmoid = sigmoid(gate)
        store(out, gate * gate_sigmoid * up)

    compiled = htp.compile_program(
        package_dir=tmp_path / "expression_swiglu_pkg",
        target="pto-a2a3sim",
        program=swiglu,
    )

    assert compiled.manifest["inputs"]["entry"] == "swiglu"
    assert compiled.manifest["target"]["backend"] == "pto"


def test_expression_first_kernel_surface_supports_scalar_literals(tmp_path):
    @kernel
    def gelu(
        x: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, x * sigmoid(x * 1.702))

    compiled = htp.compile_program(
        package_dir=tmp_path / "expression_gelu_pkg",
        target="pto-a2a3sim",
        program=gelu,
    )

    assert compiled.manifest["inputs"]["entry"] == "gelu"
    assert compiled.manifest["target"]["backend"] == "pto"


def test_expression_first_kernel_surface_supports_sub_and_div_with_literals(tmp_path):
    @kernel
    def affine(
        x: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, (x - 1.0) / 2.0)

    compiled = htp.compile_program(
        package_dir=tmp_path / "expression_affine_pkg",
        target="nvgpu-ampere",
        program=affine,
    )

    assert compiled.manifest["inputs"]["entry"] == "affine"
    assert compiled.manifest["target"]["backend"] == "nvgpu"


def test_public_routine_surface_emits_human_readable_workload_shape():
    @kernel
    def decode_step(
        hidden: buffer(dtype="f32", shape=("B", "H"), role="input"),
        weights: buffer(dtype="f32", shape=("H", "H"), role="input"),
        next_hidden: buffer(dtype="f32", shape=("B", "H"), role="output"),
        B: scalar(dtype="i32", role="shape"),
        H: scalar(dtype="i32", role="shape"),
    ) -> None:
        matmul(hidden, weights, out=next_hidden, m=B, n=H, k=H, dtype="f32")

    @program(target="nvgpu-ampere")
    def serving_routine(
        hidden: buffer(dtype="f32", shape=("B", "H"), role="input"),
        weights: buffer(dtype="f32", shape=("H", "H"), role="input"),
        next_hidden: buffer(dtype="f32", shape=("B", "H"), role="output"),
        B: scalar(dtype="i32", role="shape"),
        H: scalar(dtype="i32", role="shape"),
    ) -> None:
        fifo_channel("token_batches", dtype="f32", capacity=2)
        prefill = call(decode_step, hidden, weights, next_hidden, B, H, task="prefill")
        call(decode_step, next_hidden, weights, next_hidden, B, H, task="decode", after=prefill)

    payload = serving_routine.to_program()

    assert payload["workload"]["tasks"][0]["task_id"] == "prefill"
    assert payload["workload"]["dependencies"] == [{"src": "prefill", "dst": "decode"}]
    assert payload["workload"]["channels"][0]["name"] == "token_batches"


def test_public_routine_surface_assigns_readable_task_ids_when_omitted():
    @kernel
    def decode_step(
        hidden: buffer(dtype="f32", shape=("B", "H"), role="input"),
        weights: buffer(dtype="f32", shape=("H", "H"), role="input"),
        next_hidden: buffer(dtype="f32", shape=("B", "H"), role="output"),
        B: scalar(dtype="i32", role="shape"),
        H: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(next_hidden, hidden @ weights)

    @program(target="nvgpu-ampere")
    def serving_routine(
        hidden: buffer(dtype="f32", shape=("B", "H"), role="input"),
        weights: buffer(dtype="f32", shape=("H", "H"), role="input"),
        next_hidden: buffer(dtype="f32", shape=("B", "H"), role="output"),
        B: scalar(dtype="i32", role="shape"),
        H: scalar(dtype="i32", role="shape"),
    ) -> None:
        fifo_channel("token_batches", dtype="f32", capacity=2)
        prefill = call(decode_step, hidden, weights, next_hidden, B, H)
        call(decode_step, next_hidden, weights, next_hidden, B, H, after=prefill)

    payload = serving_routine.to_program()

    assert [task["task_id"] for task in payload["workload"]["tasks"]] == [
        "decode_step_0",
        "decode_step_1",
    ]
    assert payload["workload"]["dependencies"] == [{"src": "decode_step_0", "dst": "decode_step_1"}]


def test_expression_first_matmul_requires_rank_two_operands():
    with pytest.raises(ValueError, match="rank-2"):

        @kernel
        def bad_matmul(
            lhs: buffer(dtype="f32", shape=("M",), role="input"),
            rhs: buffer(dtype="f32", shape=("M",), role="input"),
            out: buffer(dtype="f32", shape=("M",), role="output"),
        ) -> None:
            store(out, lhs @ rhs)


def test_compile_program_accepts_traced_routine_surface(tmp_path):
    @kernel
    def decode_step(
        hidden: buffer(dtype="f32", shape=("B", "H"), role="input"),
        weights: buffer(dtype="f32", shape=("H", "H"), role="input"),
        next_hidden: buffer(dtype="f32", shape=("B", "H"), role="output"),
        B: scalar(dtype="i32", role="shape"),
        H: scalar(dtype="i32", role="shape"),
    ) -> None:
        matmul(hidden, weights, out=next_hidden, m=B, n=H, k=H, dtype="f32")

    @program(target="nvgpu-ampere")
    def serving_routine(
        hidden: buffer(dtype="f32", shape=("B", "H"), role="input"),
        weights: buffer(dtype="f32", shape=("H", "H"), role="input"),
        next_hidden: buffer(dtype="f32", shape=("B", "H"), role="output"),
        B: scalar(dtype="i32", role="shape"),
        H: scalar(dtype="i32", role="shape"),
    ) -> None:
        fifo_channel("token_batches", dtype="f32", capacity=2)
        prefill = call(decode_step, hidden, weights, next_hidden, B, H, task="prefill")
        call(decode_step, next_hidden, weights, next_hidden, B, H, task="decode", after=prefill)

    compiled = htp.compile_program(
        package_dir=tmp_path / "traced_routine_pkg",
        target="nvgpu-ampere",
        program=serving_routine,
    )

    assert compiled.manifest["inputs"]["entry"] == "serving_routine"
    assert compiled.manifest["target"]["backend"] == "nvgpu"


def test_public_kernel_surface_covers_broader_operation_helpers():
    payload = kernel(
        "rich_kernel",
        args=[
            buffer("src", dtype="f32", shape=("M", "N"), role="input"),
            buffer("dst", dtype="f32", shape=("M", "N"), role="output"),
            scalar("count", dtype="i32", role="shape"),
        ],
        ops=[
            async_copy("src", target="dst", dtype="f32"),
            cast("dst", out="tmp0", dtype="bf16"),
            broadcast("tmp0", out="tmp1", shape=("M", "N"), dtype="bf16"),
            transpose("tmp1", out="tmp2", permutation=(1, 0), dtype="bf16"),
            reduction_sum("tmp2", out="tmp3", axis=0, dtype="bf16"),
            channel_send("tmp3", channel="partials"),
            channel_recv("partials", out="tmp4", dtype="bf16"),
            barrier(),
        ],
    ).to_payload()

    assert [op["op"] for op in payload["ops"]] == [
        "async_copy",
        "cast",
        "broadcast",
        "transpose",
        "reduction_sum",
        "channel_send",
        "channel_recv",
        "barrier",
    ]


def test_public_kernel_surface_supports_implicit_staging_temporaries():
    @kernel
    def staged_gemm(
        A: buffer(dtype="f32", shape=("M", "K"), role="input"),
        B: buffer(dtype="f32", shape=("K", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        a_shared = async_copy(A, dtype="f32", memory_space="shared")
        b_shared = async_copy(B, dtype="f32", memory_space="shared")
        accum = mma(a_shared, b_shared, m=M, n=N, k=K, dtype="f32")
        store(C, accum)

    payload = staged_gemm.to_payload()

    assert payload["ops"][0]["target_memory_space"] == "shared"
    assert payload["ops"][1]["target_memory_space"] == "shared"
    assert payload["ops"][2]["op"] == "mma"
    assert payload["ops"][3]["op"] == "elementwise_unary"


def test_public_kernel_surface_supports_implicit_channel_and_reduce_temporaries():
    @kernel
    def pipeline_stage(
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
    ) -> None:
        tile_payload = channel_recv("tiles", dtype="f32", shape=("M", "N"))
        tile_summary = reduction_sum(tile_payload, axis=0, dtype="f32", shape=("N",))
        merged = channel_recv("partials", dtype="f32", shape=("N",))
        expanded = broadcast(merged, shape=("M", "N"), dtype="f32")
        channel_send(tile_summary, channel="partials")
        store(C, expanded)

    payload = pipeline_stage.to_payload()

    assert payload["ops"][0]["op"] == "channel_recv"
    assert payload["ops"][1]["op"] == "reduction_sum"
    assert payload["ops"][2]["op"] == "channel_recv"
    assert payload["ops"][3]["op"] == "broadcast"
    assert payload["ops"][4]["op"] == "channel_send"


def test_wsp_program_surface_accepts_kernel_specs_and_task_helpers():
    @kernel
    def gemm_tile(
        A: buffer(dtype="f32", shape=("M", "K"), role="input"),
        B: buffer(dtype="f32", shape=("K", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(C, A @ B)

    @wsp_program(target="nvgpu-ampere", kernel=gemm_tile)
    def gemm_workload(w) -> None:
        (
            w.launch(gemm_tile, "A", "B", "C", "M", "N", "K", task_id="gemm_main")
            .tile(block=(32, 64, 16))
            .bind(grid="block", lane="warp")
            .pipeline(depth=2, buffering="double")
            .resources(num_warps=4)
            .specialize(operator="matmul")
        )

    payload = gemm_workload.to_program()

    assert payload["kernel"]["name"] == "gemm_tile"
    assert payload["wsp"]["workload"]["tasks"][0]["task_id"] == "gemm_main"
    assert payload["wsp"]["schedule"]["pipeline"]["depth"] == 2


def test_csp_program_surface_accepts_kernel_specs_and_step_helpers():
    @kernel
    def gemm_tile(
        A: buffer(dtype="f32", shape=("M", "K"), role="input"),
        B: buffer(dtype="f32", shape=("K", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(C, A @ B)

    @csp_program(target="nvgpu-ampere", kernel=gemm_tile)
    def pipeline_demo(p) -> None:
        tiles = p.fifo("tiles", dtype="f32", capacity=2)
        p.process(
            "producer",
            task_id="p0",
            kernel=gemm_tile,
            args=("A", "B", "C", "M", "N", "K"),
        ).put(tiles)
        p.process(
            "consumer",
            task_id="p1",
            kernel=gemm_tile,
            args=("A", "B", "C", "M", "N", "K"),
        ).get(tiles)

    payload = pipeline_demo.to_program()

    assert payload["kernel"]["name"] == "gemm_tile"
    assert payload["csp"]["channels"][0]["name"] == "tiles"
    assert payload["csp"]["processes"][0]["steps"][0]["kind"] == "put"
    assert payload["csp"]["processes"][1]["steps"][0]["kind"] == "get"


def test_wsp_decorator_surface_rejects_non_kernel_spec():
    with pytest.raises(TypeError, match="KernelSpec"):
        wsp_program(target="nvgpu-ampere", kernel={"name": "raw_kernel"})


def test_csp_decorator_surface_rejects_non_kernel_spec():
    with pytest.raises(TypeError, match="KernelSpec"):
        csp_program(target="nvgpu-ampere", kernel={"name": "raw_kernel"})


def test_compile_program_rejects_broken_program_surface(tmp_path):
    class BrokenProgram:
        def to_program(self) -> list[str]:
            return ["not", "a", "mapping"]

    try:
        htp.compile_program(
            package_dir=tmp_path / "broken_surface",
            target="pto-a2a3sim",
            program=BrokenProgram(),
        )
    except TypeError as exc:
        assert "to_program()" in str(exc)
    else:
        raise AssertionError("compile_program should reject broken public program surfaces")


def test_ark_surface_builds_ampere_program_payload():
    @ark.build(target="nvgpu-ampere", hardware=ark.ampere())
    def ampere_mainloop():
        A = ark.tensor("A", dtype="f16", shape=("M", "K"), role="input", memory="global")
        B = ark.tensor("B", dtype="f16", shape=("K", "N"), role="input", memory="global")
        C = ark.tensor("C", dtype="f32", shape=("M", "N"), role="output", memory="global")
        AS = ark.tensor("AS", dtype="f16", shape=("BM", "BK"), memory="shared")
        BS = ark.tensor("BS", dtype="f16", shape=("BK", "BN"), memory="shared")
        AR = ark.tensor("AR", dtype="f16", shape=("WM", "WK"), memory="register")
        BR = ark.tensor("BR", dtype="f16", shape=("WK", "WN"), memory="register")
        CR = ark.tensor("CR", dtype="f32", shape=("WM", "WN"), memory="register")

        m_block = ark.axis("m_block", 2)
        n_block = ark.axis("n_block", 2)
        k_outer = ark.axis("k_outer", 4)
        warp_m = ark.axis("warp_m", 2)
        warp_n = ark.axis("warp_n", 2)

        with ark.spatial("block", m_block, n_block, swizzle=[8, None]):
            with ark.pipeline(k_outer, stages=3):
                ark.cp_async(AS, A, channel="shared_pipe")
                ark.cp_async(BS, B, channel="shared_pipe")
                with ark.spatial("warp", warp_m, warp_n):
                    ark.ldmatrix(AR, AS)
                    ark.ldmatrix(BR, BS)
                    ark.mma_sync(CR, AR, BR, accum=CR, shape=(16, 8, 16))
            ark.commit(C, CR)
        assert isinstance(A, KernelValue)
        assert A.memory_space == "global"
        assert A.axis_layout == ("M", "K")
        assert AS.axis_layout == ("BM", "BK")
        return A, B, C

    payload = ampere_mainloop.to_program()

    assert payload["target"] == {"backend": "nvgpu", "option": "ampere"}
    assert payload["ark"]["hardware"]["profile"] == "ampere"
    assert payload["ark"]["hardware"]["memory_spaces"] == ["global", "shared", "register"]
    assert payload["kernel"]["args"][0]["memory_space"] == "global"
    assert payload["kernel"]["args"][0]["axis_layout"] == ["M", "K"]
    assert [op["op"] for op in payload["kernel"]["ops"]] == [
        "cp_async",
        "cp_async",
        "ldmatrix",
        "ldmatrix",
        "mma_sync",
        "commit",
    ]


def test_ark_surface_rejects_blackwell_only_instruction_on_ampere(tmp_path):
    @ark.build(target="nvgpu-ampere", hardware=ark.ampere())
    def bad_blackwell_program():
        A = ark.tensor("A", dtype="bf16", shape=("M", "K"), role="input", memory="global")
        B = ark.tensor("B", dtype="bf16", shape=("K", "N"), role="input", memory="global")
        C = ark.tensor("C", dtype="f32", shape=("M", "N"), role="output", memory="global")
        TS = ark.tensor("TS", dtype="bf16", shape=("BM", "BK"), memory="shared")
        TC = ark.tensor("TC", dtype="f32", shape=("BM", "BN"), memory="tensor")

        with ark.spatial("cluster", ark.axis("cluster_m", 2), ark.axis("cluster_n", 2)):
            ark.tma_load(TS, A, channel="cluster_pipe")
            ark.wgmma(TC, TS, B, accum=TC, shape=(64, 128, 16), channel="cluster_pipe")
            ark.tma_store(C, TC, channel="store_pipe")
        return A, B, C

    with pytest.raises(RuntimeError, match="wgmma|tma_load|tma_store"):
        htp.compile_program(
            package_dir=tmp_path / "bad_ark_ampere",
            target="nvgpu-ampere",
            program=bad_blackwell_program,
        )


def test_ark_surface_reuses_native_kernel_value_objects():
    @ark.build(target="nvgpu-ampere", hardware=ark.ampere())
    def native_value_program():
        A = ark.attach(
            value("A", dtype="f16", shape=("M", "K"), role="input"),
            memory="global",
        )
        B = ark.attach(
            value("B", dtype="f16", shape=("K", "N"), role="input"),
            memory="global",
        )
        C = ark.attach(
            value("C", dtype="f32", shape=("M", "N"), role="output"),
            memory="global",
            axis_layout=("row", "col"),
            attrs={"tile_hint": "accumulator"},
        )
        ark.commit(C, C)
        return A, B, C

    payload = native_value_program.to_program()
    c_arg = next(item for item in payload["kernel"]["args"] if item["name"] == "C")

    assert c_arg["axis_layout"] == ["row", "col"]
    assert c_arg["attrs"] == {"tile_hint": "accumulator"}
