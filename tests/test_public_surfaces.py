from __future__ import annotations

import htp
from htp.kernel import (
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
    reduction_sum,
    scalar,
    transpose,
)
from htp.routine import call, fifo_channel, program


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
