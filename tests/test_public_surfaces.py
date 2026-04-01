from __future__ import annotations

import pytest

import htp
import htp.csp as csp_module
import htp.routine as routine_module
import htp.wsp as wsp_module
from htp import ark
from htp.csp import program as csp_program
from htp.ir.core.semantics import KernelIR, WorkloadIR
from htp.ir.dialects.csp import CSPProcessStep as TypedCSPProcessStep
from htp.ir.dialects.wsp import WSPStageSpec, WSPStageStep
from htp.ir.frontends import resolve_frontend
from htp.ir.program.module import ProgramModule
from htp.kernel import (
    KernelSpec,
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
    region,
    registers,
    scalar,
    scratch_array,
    serial,
    shared_array,
    sigmoid,
    store,
    transpose,
    unroll,
    value,
)
from htp.routine import call, fifo_channel, program
from htp.types import bf16, channel_type, dim, f32, index, shape, shard, tensor
from htp.wsp import program as wsp_program


def _frontend_probe_module(entry: str) -> ProgramModule:
    return ProgramModule.from_program_dict(
        {
            "entry": entry,
            "canonical_ast": {"schema": "htp.program_ast.v1", "program": {"entry": entry}},
            "kernel_ir": {},
            "workload_ir": {},
        }
    )


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


def test_kernel_surface_exposes_program_module_and_compiler_prefers_it(tmp_path):
    @kernel
    def affine_mix(
        lhs: buffer(dtype="f32", shape=("size",), role="input"),
        rhs: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, lhs + rhs)

    module = affine_mix.to_program_module()

    assert isinstance(module, ProgramModule)
    assert isinstance(module.items.kernel_ir, KernelIR)
    assert isinstance(module.items.workload_ir, WorkloadIR)
    assert module.items.kernel_ir.entry == "affine_mix"
    assert module.items.workload_ir.tasks[0].kernel == "affine_mix"
    assert module.meta["active_dialects"] == ["htp.core", "htp.kernel"]
    assert module.meta["dialect_activation"]["requested"] == ["htp.core", "htp.kernel"]

    class ModuleOnlySurface:
        def to_program_module(self) -> ProgramModule:
            return module

        def to_program(self) -> dict[str, object]:
            raise AssertionError("compile_program should prefer to_program_module()")

    compiled = htp.compile_program(
        package_dir=tmp_path / "module_surface_pkg",
        target="pto-a2a3sim",
        program=ModuleOnlySurface(),
    )

    assert compiled.manifest["inputs"]["entry"] == "affine_mix"
    assert compiled.manifest["target"]["backend"] == "pto"


def test_kernel_surface_is_built_through_registered_frontend_rule() -> None:
    spec = resolve_frontend(KernelSpec(name="affine", args=(), ops=()))

    assert spec is not None
    assert spec.frontend_id == "htp.kernel.KernelSpec"
    assert spec.rule is not None
    assert spec.build_program_module is None


def test_routine_wsp_and_csp_surfaces_are_built_through_registered_frontend_rules() -> None:
    @kernel
    def affine_mix(
        lhs: buffer(dtype="f32", shape=("size",), role="input"),
        rhs: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, lhs + rhs)

    @program(target="nvgpu-ampere")
    def serving_routine(
        lhs: buffer(dtype="f32", shape=("size",), role="input"),
        rhs: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        call(affine_mix, lhs, rhs, out, size, task="run")

    @wsp_program(target="nvgpu-ampere", kernel=affine_mix)
    def tiled_workload(w) -> None:
        w.launch(task_id="run").tile(block=(64, 64, 16)).resources(num_warps=4)

    @csp_program(kernel=affine_mix, target="nvgpu-ampere")
    def streaming_workload(p) -> None:
        tiles = p.fifo("tiles", dtype="f32", capacity=1)
        p.process("dispatch", task_id="dispatch").put(tiles).compute("pack_tile", source=p.args.lhs)

    for surface, frontend_id in (
        (serving_routine, "htp.routine.ProgramSpec"),
        (tiled_workload, "htp.wsp.WSPProgramSpec"),
        (streaming_workload, "htp.csp.CSPProgramSpec"),
    ):
        spec = resolve_frontend(surface)

        assert spec is not None
        assert spec.frontend_id == frontend_id
        assert spec.rule is not None
        assert spec.build_program_module is None


def test_public_surface_program_modules_delegate_to_registered_frontend_builders(monkeypatch) -> None:
    expected_routine = _frontend_probe_module("routine_frontend_probe")
    expected_wsp = _frontend_probe_module("wsp_frontend_probe")
    expected_csp = _frontend_probe_module("csp_frontend_probe")

    class StubFrontend:
        def __init__(self, expected_surface, result: ProgramModule) -> None:
            self.expected_surface = expected_surface
            self.result = result

        def build(self, surface) -> ProgramModule:
            assert surface is self.expected_surface
            return self.result

    routine_spec = routine_module.ProgramSpec(
        entry="routine_frontend_probe",
        kernel=KernelSpec(name="affine", args=(), ops=()),
        tasks=(),
    )
    wsp_spec = wsp_module.WSPProgramSpec(
        entry="wsp_frontend_probe",
        target={},
        kernel=KernelSpec(name="affine", args=(), ops=()),
        tasks=(),
        channels=(),
        dependencies=(),
        schedule=wsp_module.WSPScheduleSpec(),
    )
    csp_spec = csp_module.CSPProgramSpec(
        entry="csp_frontend_probe",
        target={},
        kernel=KernelSpec(name="affine", args=(), ops=()),
        channels=(),
        processes=(),
    )

    monkeypatch.setattr(
        routine_module,
        "resolve_frontend",
        lambda surface: StubFrontend(routine_spec, expected_routine),
    )
    monkeypatch.setattr(
        wsp_module,
        "resolve_frontend",
        lambda surface: StubFrontend(wsp_spec, expected_wsp),
    )
    monkeypatch.setattr(
        csp_module,
        "resolve_frontend",
        lambda surface: StubFrontend(csp_spec, expected_csp),
    )

    assert routine_spec.to_program_module() is expected_routine
    assert wsp_spec.to_program_module() is expected_wsp
    assert csp_spec.to_program_module() is expected_csp


def test_public_type_surface_drives_kernel_and_channel_annotations(tmp_path):
    @kernel
    def typed_decode(
        x: buffer(
            type=tensor(f32, shape(dim("B"), dim("H")), distribution=(shard(axis=0), "replicate")),
            role="input",
        ),
        w: buffer(type=tensor(bf16, shape(dim("H"), dim("H"))), role="input"),
        y: buffer(type=tensor(f32, shape(dim("B"), dim("H"))), role="output"),
        B: scalar(dtype=index, role="shape"),
    ) -> None:
        store(y, x @ w)

    @program(target="nvgpu-ampere")
    def typed_serving(
        x: buffer(
            type=tensor(f32, shape(dim("B"), dim("H")), distribution=(shard(axis=0), "replicate")),
            role="input",
        ),
        w: buffer(type=tensor(bf16, shape(dim("H"), dim("H"))), role="input"),
        y: buffer(type=tensor(f32, shape(dim("B"), dim("H"))), role="output"),
        B: scalar(dtype=index, role="shape"),
    ) -> None:
        fifo_channel("tokens", type=channel_type(f32, capacity=2))
        prefill = call(
            typed_decode,
            x,
            w,
            y,
            B,
            task="prefill",
            phase="prefill",
            role="compute",
            state="kv_fill",
        )
        call(
            typed_decode,
            y,
            w,
            y,
            B,
            task="decode",
            after=prefill,
            phase="decode",
            role="compute",
            state="token_step",
        )

    compiled = htp.compile_program(
        package_dir=tmp_path / "typed_surface_pkg",
        target="nvgpu-ampere",
        program=typed_serving,
    )

    stage_id = compiled.manifest["stages"]["current"]
    state_json = (compiled.package_dir / "ir" / "stages" / stage_id / "state.json").read_text()

    assert '"kind": "serving_routine"' in state_json
    assert '"phase": "prefill"' in state_json
    assert '"state": "kv_fill"' in state_json
    assert '"name": "index"' in state_json
    assert '"axis": "0"' in state_json or '"axis": 0' in state_json


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


def test_public_routine_surface_exposes_program_module(tmp_path):
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

    module = serving_routine.to_program_module()

    assert isinstance(module, ProgramModule)
    assert isinstance(module.items.kernel_ir, KernelIR)
    assert isinstance(module.items.workload_ir, WorkloadIR)
    assert module.items.workload_ir.entry == "serving_routine"
    assert [task.task_id for task in module.items.workload_ir.tasks] == ["prefill", "decode"]
    assert module.items.workload_ir.dependencies == ({"src": "prefill", "dst": "decode"},)
    assert module.meta["active_dialects"] == ["htp.core", "htp.kernel", "htp.routine"]
    assert module.items.workload_ir.routine == {
        "kind": "routine",
        "entry": "serving_routine",
        "target": {"backend": "nvgpu", "option": "ampere"},
    }

    compiled = htp.compile_program(
        package_dir=tmp_path / "routine_module_pkg",
        target="nvgpu-ampere",
        program=serving_routine,
    )

    assert compiled.manifest["inputs"]["entry"] == "serving_routine"
    assert compiled.manifest["target"]["backend"] == "nvgpu"


def test_public_kernel_surface_covers_collective_and_tensor_reshape_ops():
    payload = kernel(
        "collective_kernel",
        args=[
            buffer(
                "src", dtype="f32", shape=("M", "N"), role="input", distribution=("replicate", shard(axis=1))
            ),
            buffer("tmp", dtype="f32", shape=("M", "N"), role="temp"),
            buffer("out", dtype="f32", shape=("M", "N"), role="output"),
        ],
        ops=[
            {"op": "slice", "source": "src", "out": "tmp", "offsets": [0, 0], "sizes": ["M", "N"]},
            {"op": "allgather", "source": "tmp", "out": "tmp", "axis": 1, "mesh_axis": 1},
            {"op": "reduce_scatter", "source": "tmp", "out": "out", "axis": 1, "mesh_axis": 1},
            {"op": "concat", "inputs": ["tmp", "out"], "out": "out", "axis": 0},
        ],
    ).to_payload()

    assert [op["op"] for op in payload["ops"]] == [
        "slice",
        "allgather",
        "reduce_scatter",
        "concat",
    ]


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


def test_public_kernel_surface_supports_explicit_scratch_arrays_and_memory_scopes():
    @kernel
    def staged_gemm(
        A: buffer(dtype="f32", shape=("M", "K"), role="input"),
        B: buffer(dtype="f32", shape=("K", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        a_tiles = shared_array("a_tile", count=2, dtype="f32", shape=("M", "K"))
        b_tiles = shared_array("b_tile", count=2, dtype="f32", shape=("K", "N"))
        acc = registers("acc", dtype="f32", shape=("M", "N"))
        for stage in unroll(range(2), name="stage"):
            async_copy(A, target=a_tiles[stage], dtype="f32")
            async_copy(B, target=b_tiles[stage], dtype="f32")
            barrier()
            tile_acc = mma(a_tiles[stage], b_tiles[stage], m=M, n=N, k=K, dtype="f32")
            acc = tile_acc if stage == 0 else acc + tile_acc
        store(C, acc)

    payload = staged_gemm.to_payload()

    assert payload["ops"][0]["target"] == "a_tile_0"
    assert payload["ops"][0]["target_memory_space"] == "shared"
    assert payload["ops"][1]["target"] == "b_tile_0"
    assert payload["ops"][3]["attrs"]["regions"][0] == {
        "kind": "loop",
        "modifier": "unroll",
        "iteration": 0,
        "var": "stage",
        "value": 0,
    }
    assert payload["ops"][7]["attrs"]["regions"][0]["iteration"] == 1


def test_public_kernel_surface_supports_tile_views_with_semantic_loop_indices():
    @kernel
    def tiled_mainloop(
        A: buffer(dtype="f32", shape=("M", "K"), role="input"),
        B: buffer(dtype="f32", shape=("K", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    ) -> None:
        a_tiles = shared_array("a_tile", count=2, dtype="f32", shape=("M", 16))
        b_tiles = shared_array("b_tile", count=2, dtype="f32", shape=(16, "N"))
        for stage in unroll(range(2), name="stage"):
            k0 = stage * 16
            a_view = A[:, k0 : k0 + 16]
            b_view = B[k0 : k0 + 16, :]
            async_copy(a_view, target=a_tiles[stage], dtype="f32")
            async_copy(b_view, target=b_tiles[stage], dtype="f32")
            barrier()
            tile_acc = mma(a_tiles[stage], b_tiles[stage], dtype="f32")
            store(C, tile_acc)

    payload = tiled_mainloop.to_payload()
    slice_ops = [op for op in payload["ops"] if op["op"] == "slice"]

    assert slice_ops[0]["offsets"] == [0, 0]
    assert slice_ops[0]["sizes"] == ["M", 16]
    assert slice_ops[0]["offset_exprs"] == ["0", "stage * 16"]
    assert slice_ops[1]["offset_exprs"] == ["stage * 16", "0"]
    assert slice_ops[2]["offsets"] == [0, 16]
    assert slice_ops[2]["offset_exprs"] == ["0", "stage * 16"]


def test_public_kernel_surface_supports_region_annotations_inside_loops():
    @kernel
    def staged_epilogue(
        A: buffer(dtype="f32", shape=("M", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    ) -> None:
        tiles = scratch_array("tiles", count=2, dtype="f32", shape=("M", "N"), memory_space="shared")
        for stage in serial(range(2), name="stage"):
            with region("pipeline_stage", phase="steady"):
                async_copy(A, target=tiles[stage], dtype="f32")
                barrier()
        store(C, tiles[0])

    payload = staged_epilogue.to_payload()

    assert payload["ops"][0]["attrs"]["regions"] == [
        {"kind": "loop", "modifier": "serial", "iteration": 0, "var": "stage", "value": 0},
        {"kind": "pipeline_stage", "phase": "steady"},
    ]
    assert payload["ops"][3]["attrs"]["regions"][0]["iteration"] == 1


def test_scratch_array_requires_positive_count():
    with pytest.raises(ValueError, match="count > 0"):
        scratch_array("tiles", count=0, dtype="f32", shape=("M", "N"), memory_space="shared")


def test_kernel_slice_syntax_rejects_step_values():
    with pytest.raises(ValueError, match="step"):

        @kernel
        def bad_slice(
            A: buffer(dtype="f32", shape=("M", "N"), role="input"),
            C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        ) -> None:
            store(C, A[0:16:2, :])


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


def test_wsp_program_surface_exposes_program_module(tmp_path):
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
            w.mainloop(task_id="mma_tiles")
            .tile(block=(32, 64, 16))
            .bind(grid="block", lane="warp")
            .pipeline(depth=2, buffering="double")
            .resources(num_warps=4)
            .specialize(operator="matmul")
        )

    module = gemm_workload.to_program_module()

    assert isinstance(module, ProgramModule)
    assert module.meta["active_dialects"] == ["htp.core", "htp.kernel", "htp.wsp"]
    assert module.items.workload_ir.routine == {
        "kind": "wsp",
        "entry": "gemm_workload",
        "schedule": {
            "tile": {"block": [32, 64, 16]},
            "bind": {"grid": "block", "lane": "warp"},
            "pipeline": {"depth": 2, "buffering": "double"},
            "resources": {"num_warps": 4},
            "specialize": {"operator": "matmul"},
        },
        "target": {"backend": "nvgpu", "option": "ampere"},
    }

    compiled = htp.compile_program(
        package_dir=tmp_path / "wsp_module_pkg",
        target="nvgpu-ampere",
        program=gemm_workload,
    )

    assert compiled.manifest["inputs"]["entry"] == "gemm_workload"


def test_wsp_mainloop_surface_carries_roles_dependencies_and_stage_plan():
    @kernel
    def gemm_tile(
        A: buffer(dtype="f32", shape=("M", "K"), role="input"),
        B: buffer(dtype="f32", shape=("K", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        tile_a = async_copy(A, dtype="f32", memory_space="shared")
        tile_b = async_copy(B, dtype="f32", memory_space="shared")
        barrier()
        store(C, mma(tile_a, tile_b, m=M, n=N, k=K, dtype="f32"))

    @wsp_program(target="nvgpu-ampere", kernel=gemm_tile)
    def gemm_workload(w) -> None:
        load = (
            w.launch(gemm_tile, "A", "B", "C", "M", "N", "K", task_id="load_tiles")
            .role("producer")
            .prologue("cp_async(A->shared)", "cp_async(B->shared)")
        )
        (
            w.mainloop(gemm_tile, "A", "B", "C", "M", "N", "K", task_id="mma_tiles")
            .after(load)
            .tile(block=(64, 128, 32))
            .bind(grid="block", lane="warp")
            .pipeline(depth=3, buffering="double")
            .resources(num_warps=4)
            .role("consumer")
            .steady("ldmatrix", "mma_sync", "advance")
            .epilogue("store(C)")
        )

    payload = gemm_workload.to_program()

    tasks = payload["wsp"]["workload"]["tasks"]
    assert [task["task_id"] for task in tasks] == ["load_tiles", "mma_tiles"]
    assert tasks[0]["attrs"]["role"] == "producer"
    assert tasks[0]["attrs"]["stages"][0] == {
        "name": "prologue",
        "steps": ["cp_async(A->shared)", "cp_async(B->shared)"],
    }
    assert tasks[1]["kind"] == "wsp_mainloop"
    assert tasks[1]["attrs"]["role"] == "consumer"
    assert tasks[1]["attrs"]["stages"][1] == {"name": "epilogue", "steps": ["store(C)"]}
    assert payload["wsp"]["workload"]["dependencies"] == [{"src": "load_tiles", "dst": "mma_tiles"}]


def test_wsp_surface_supports_defaults_bound_args_and_structured_stage_bodies():
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
        with w.defaults(
            tile={"block": (64, 128, 32)},
            bind={"grid": "block", "lane": "warp"},
            pipeline={"depth": 3, "buffering": "double"},
            resources={"num_warps": 4},
        ):
            load = w.launch(
                gemm_tile,
                w.args.A,
                w.args.B,
                w.args.C,
                w.args.M,
                w.args.N,
                w.args.K,
                task_id="load_tiles",
            ).role("producer")
            load.prologue().step("cp_async", source=w.args.A, target="a_tile")
            load.prologue().step("cp_async", source=w.args.B, target="b_tile")

            mma_stage = (
                w.mainloop(
                    gemm_tile,
                    w.args.A,
                    w.args.B,
                    w.args.C,
                    w.args.M,
                    w.args.N,
                    w.args.K,
                    task_id="mma_tiles",
                )
                .after(load)
                .role("consumer")
            )
            mma_stage.steady().step("ldmatrix", source="a_tile")
            mma_stage.steady().step("mma_sync", accum="acc")
            mma_stage.epilogue().step("store", target=w.args.C)

    payload = gemm_workload.to_program()

    tasks = payload["wsp"]["workload"]["tasks"]
    assert tasks[0]["args"] == ["A", "B", "C", "M", "N", "K"]
    assert tasks[0]["attrs"]["schedule"] == {
        "tile": {"block": [64, 128, 32]},
        "bind": {"grid": "block", "lane": "warp"},
        "pipeline": {"depth": 3, "buffering": "double"},
        "resources": {"num_warps": 4},
    }
    assert tasks[0]["attrs"]["stages"][0] == {
        "name": "prologue",
        "steps": [
            {"kind": "step", "op": "cp_async", "source": "A", "target": "a_tile"},
            {"kind": "step", "op": "cp_async", "source": "B", "target": "b_tile"},
        ],
    }
    assert tasks[1]["attrs"]["stages"][0] == {
        "name": "steady",
        "steps": [
            {"kind": "step", "op": "ldmatrix", "source": "a_tile"},
            {"kind": "step", "op": "mma_sync", "accum": "acc"},
        ],
    }
    assert tasks[1]["attrs"]["stages"][1] == {
        "name": "epilogue",
        "steps": [{"kind": "step", "op": "store", "target": "C"}],
    }


def test_csp_program_spec_uses_typed_process_steps() -> None:
    @kernel
    def affine_mix(
        lhs: buffer(dtype="f32", shape=("size",), role="input"),
        rhs: buffer(dtype="f32", shape=("size",), role="input"),
        out: buffer(dtype="f32", shape=("size",), role="output"),
        size: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, lhs + rhs)

    @csp_program(kernel=affine_mix, target="nvgpu-ampere")
    def streaming_workload(p) -> None:
        tiles = p.fifo("tiles", dtype="f32", capacity=2)
        partials = p.fifo("partials", dtype="f32", capacity=2)
        p.process("dispatch", task_id="dispatch").role("source").get(tiles).compute_step(
            "prepare_tile", source=p.args.lhs, count=2
        ).put(partials)

    process_spec = streaming_workload.processes[0]

    assert process_spec.steps
    assert all(isinstance(step, TypedCSPProcessStep) for step in process_spec.steps)
    assert process_spec.steps[0].kind == "get"
    assert process_spec.steps[1].kind == "compute"
    assert process_spec.steps[1].attrs == {"op": "prepare_tile", "source": "lhs", "count": 2}
    assert process_spec.steps[2].kind == "put"

    payload = process_spec.to_payload()

    assert payload["steps"] == [
        {"kind": "get", "channel": "tiles", "count": 1},
        {"kind": "compute", "op": "prepare_tile", "source": "lhs", "count": 2},
        {"kind": "put", "channel": "partials", "count": 1},
    ]

    rebuilt = csp_module.CSPProcessSpec.from_payload(payload)

    assert all(isinstance(step, TypedCSPProcessStep) for step in rebuilt.steps)
    assert rebuilt.steps[1].attrs == {"op": "prepare_tile", "source": "lhs", "count": 2}


def test_wsp_program_spec_uses_typed_stage_objects() -> None:
    @kernel
    def affine_mix(
        lhs: buffer(dtype="f32", shape=("M", "K"), role="input"),
        rhs: buffer(dtype="f32", shape=("K", "N"), role="input"),
        out: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(out, lhs @ rhs)

    @wsp_program(target="nvgpu-ampere", kernel=affine_mix)
    def tiled(w) -> None:
        (
            w.mainloop(task_id="main")
            .role("consumer")
            .prologue()
            .step("cp_async", source=w.args.lhs, target="a_stage")
            .step("cp_async", source=w.args.rhs, target="b_stage")
        )

    stages = tiled.tasks[0].attrs["stages"]

    assert isinstance(stages[0], WSPStageSpec)
    assert isinstance(stages[0].steps[0], WSPStageStep)
    assert stages[0].steps[0].op == "cp_async"
    assert stages[0].steps[0].attrs == {"source": "lhs", "target": "a_stage"}


def test_wsp_ast_frontend_supports_nested_task_functions() -> None:
    @kernel
    def affine_mix(
        A: buffer(dtype="f32", shape=("M", "K"), role="input"),
        B: buffer(dtype="f32", shape=("K", "N"), role="input"),
        C: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
        K: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(C, A @ B)

    @wsp_program(target="nvgpu-ampere", kernel=affine_mix)
    def tiled(w) -> None:
        @w.task(task_id="load_tiles", role="producer")
        def load_tiles() -> None:
            w.step("cp_async", stage="prologue", source=w.args.A, target="a_tile")
            w.step("cp_async", stage="prologue", source=w.args.B, target="b_tile")

        @w.mainloop(
            task_id="mma_tiles",
            role="consumer",
            after=load_tiles,
            tile={"block": (64, 128, 32)},
            bind={"grid": "block", "lane": "warp"},
            pipeline={"depth": 2, "buffering": "double"},
            resources={"num_warps": 4},
        )
        def mma_tiles() -> None:
            w.step("barrier", stage="steady")
            w.step("mma_sync", stage="steady", accum="acc")

    payload = tiled.to_program()
    module = tiled.to_program_module()

    assert payload["wsp"]["workload"]["dependencies"] == [{"src": "load_tiles", "dst": "mma_tiles"}]
    assert payload["wsp"]["workload"]["tasks"][0]["attrs"]["stages"][0]["steps"][0]["op"] == "cp_async"
    assert payload["wsp"]["workload"]["tasks"][1]["kind"] == "wsp_mainloop"
    assert module.meta["frontend_capture"] == "ast"
    assert module.items.typed_items[0].name == "tiled"


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


def test_csp_program_surface_exposes_program_module(tmp_path):
    @kernel
    def pipeline_stage(
        X: buffer(dtype="f32", shape=("M", "N"), role="input"),
        Y: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(Y, X + X)

    @csp_program(target="nvgpu-ampere", kernel=pipeline_stage)
    def pipeline_demo(p) -> None:
        tiles = p.fifo("tiles", dtype="f32", capacity=2)
        p.process("dispatch", task_id="dispatch").role("producer").put(tiles)
        p.process("consume", task_id="consume").role("consumer").get(tiles)

    module = pipeline_demo.to_program_module()

    assert isinstance(module, ProgramModule)
    assert module.meta["active_dialects"] == ["htp.core", "htp.kernel", "htp.csp"]
    assert [item["dialect_id"] for item in module.meta["dialect_activation"]["resolved"]] == [
        "htp.core",
        "htp.kernel",
        "htp.csp",
    ]
    assert module.items.workload_ir.routine == {
        "kind": "csp",
        "entry": "pipeline_demo",
        "target": {"backend": "nvgpu", "option": "ampere"},
    }
    assert [process["name"] for process in module.items.workload_ir.processes] == ["dispatch", "consume"]
    assert module.items.workload_ir.tasks[0].attrs == {"name": "dispatch", "role": "producer"}

    compiled = htp.compile_program(
        package_dir=tmp_path / "csp_module_pkg",
        target="nvgpu-ampere",
        program=pipeline_demo,
    )

    assert compiled.manifest["inputs"]["entry"] == "pipeline_demo"


def test_csp_process_surface_carries_role_and_compute_steps():
    @kernel
    def pipeline_stage(
        X: buffer(dtype="f32", shape=("M", "N"), role="input"),
        Y: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
    ) -> None:
        tile_payload = channel_recv("tiles", dtype="f32", shape=("M", "N"))
        summary = reduction_sum(tile_payload, axis=0, dtype="f32", shape=("N",))
        channel_send(summary, channel="partials")
        store(Y, broadcast(summary, shape=("M", "N"), dtype="f32"))

    @csp_program(target="nvgpu-ampere", kernel=pipeline_stage)
    def pipeline_demo(p) -> None:
        tiles = p.fifo("tiles", dtype="f32", capacity=2)
        partials = p.fifo("partials", dtype="f32", capacity=1)
        (
            p.process("dispatch", task_id="dispatch", kernel=pipeline_stage, args=("X", "Y", "M", "N"))
            .role("producer")
            .compute("pack_tile", source="X")
            .put(tiles)
        )
        (
            p.process("combine", task_id="combine", kernel=pipeline_stage, args=("X", "Y", "M", "N"))
            .role("router")
            .get(tiles)
            .compute("reduce_partials", channel="tiles")
            .put(partials)
        )

    payload = pipeline_demo.to_program()

    assert payload["csp"]["processes"][0]["role"] == "producer"
    assert payload["csp"]["processes"][0]["steps"][0] == {
        "kind": "compute",
        "name": "pack_tile",
        "source": "X",
    }
    assert payload["csp"]["processes"][1]["steps"][1] == {
        "kind": "compute",
        "name": "reduce_partials",
        "channel": "tiles",
    }


def test_csp_ast_frontend_supports_nested_process_functions() -> None:
    @kernel
    def pipeline_stage(
        X: buffer(dtype="f32", shape=("M", "N"), role="input"),
        Y: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
    ) -> None:
        store(Y, X + X)

    @csp_program(target="nvgpu-ampere", kernel=pipeline_stage)
    def pipeline_demo(c) -> None:
        tiles = c.fifo("tiles", dtype="f32", capacity=2)
        partials = c.fifo("partials", dtype="f32", capacity=1)

        @c.process(task_id="dispatch", role="producer")
        def dispatch() -> None:
            tile = c.get(tiles)
            c.compute("pack_tile", source=c.args.X, tile=tile)
            c.put(partials)

        @c.process(task_id="combine", role="consumer", args=(c.args.X, c.args.Y, c.args.M, c.args.N))
        def combine() -> None:
            payload = c.get(partials)
            c.compute_step("reduce_partials", value=payload)
            c.put(tiles)

    payload = pipeline_demo.to_program()
    module = pipeline_demo.to_program_module()

    assert [channel["name"] for channel in payload["csp"]["channels"]] == ["tiles", "partials"]
    assert payload["csp"]["processes"][0]["steps"][1] == {
        "kind": "compute",
        "name": "pack_tile",
        "source": "X",
        "tile": "tile",
    }
    assert payload["csp"]["processes"][1]["steps"][1] == {
        "kind": "compute",
        "op": "reduce_partials",
        "value": "payload",
    }
    assert module.meta["frontend_capture"] == "ast"
    assert module.items.typed_items[0].name == "pipeline_demo"


def test_csp_surface_supports_bound_args_and_structured_process_bodies():
    @kernel
    def pipeline_stage(
        X: buffer(dtype="f32", shape=("M", "N"), role="input"),
        Y: buffer(dtype="f32", shape=("M", "N"), role="output"),
        M: scalar(dtype="i32", role="shape"),
        N: scalar(dtype="i32", role="shape"),
    ) -> None:
        tile_payload = channel_recv("tiles", dtype="f32", shape=("M", "N"))
        summary = reduction_sum(tile_payload, axis=0, dtype="f32", shape=("N",))
        channel_send(summary, channel="partials")
        store(Y, broadcast(summary, shape=("M", "N"), dtype="f32"))

    @csp_program(target="nvgpu-ampere", kernel=pipeline_stage)
    def pipeline_demo(p) -> None:
        tiles = p.fifo("tiles", dtype="f32", capacity=2)
        partials = p.fifo("partials", dtype="f32", capacity=1)

        dispatch = p.process("dispatch", task_id="dispatch").role("producer")
        dispatch.compute_step("pack_tile", source=p.args.X)
        dispatch.put(tiles)

        combine = p.process("combine", task_id="combine").role("router")
        combine.get(tiles)
        combine.compute_step("reduce_partials", channel=tiles)
        combine.put(partials)

    payload = pipeline_demo.to_program()

    assert payload["csp"]["processes"][0]["args"] == ["X", "Y", "M", "N"]
    assert payload["csp"]["processes"][0]["steps"][0] == {
        "kind": "compute",
        "op": "pack_tile",
        "source": "X",
    }
    assert payload["csp"]["processes"][1]["steps"][1] == {
        "kind": "compute",
        "op": "reduce_partials",
        "channel": "tiles",
    }


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
