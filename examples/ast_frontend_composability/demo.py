from __future__ import annotations

from typing import Any

from htp.csp import program as csp_program
from htp.ir.core.semantics import WorkloadIR
from htp.ir.frontends import FrontendSyntaxError
from htp.ir.interpreters.entrypoints import NODE_PROGRAM_INTERPRETER_ID
from htp.ir.program.module import ProgramEntrypoint, ProgramItems, ProgramModule
from htp.kernel import buffer, kernel, scalar, store
from htp.wsp import program as wsp_program


@kernel
def tile_kernel(
    A: buffer(dtype="f32", shape=("M", "K"), role="input"),
    B: buffer(dtype="f32", shape=("K", "N"), role="input"),
    C: buffer(dtype="f32", shape=("M", "N"), role="output"),
    M: scalar(dtype="i32", role="shape"),
    N: scalar(dtype="i32", role="shape"),
    K: scalar(dtype="i32", role="shape"),
) -> None:
    store(C, A @ B)


@wsp_program(target="nvgpu-ampere", kernel=tile_kernel)
def scheduled_tiles(w) -> None:
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


@csp_program(target="nvgpu-ampere", kernel=tile_kernel)
def streamed_tiles(c) -> None:
    tiles = c.fifo("tiles", dtype="f32", capacity=2)
    partials = c.fifo("partials", dtype="f32", capacity=1)

    @c.process(task_id="dispatch", role="producer")
    def dispatch() -> None:
        tile = c.get(tiles)
        c.compute("pack_tile", source=c.args.A, tile=tile)
        c.put(partials)

    @c.process(
        task_id="combine", role="consumer", args=(c.args.A, c.args.B, c.args.C, c.args.M, c.args.N, c.args.K)
    )
    def combine() -> None:
        partial = c.get(partials)
        c.compute_step("reduce_partials", value=partial)
        c.put(tiles)


def build_composed_module() -> ProgramModule:
    wsp_module = scheduled_tiles.to_program_module()
    csp_module = streamed_tiles.to_program_module()
    return ProgramModule(
        items=ProgramItems(
            canonical_ast={
                "schema": "htp.program_ast.v1",
                "program": {
                    "entry": "run",
                    "wsp": scheduled_tiles.to_program(),
                    "csp": streamed_tiles.to_program(),
                },
            },
            kernel_ir=wsp_module.items.kernel_ir,
            workload_ir=WorkloadIR(
                entry="run",
                tasks=wsp_module.items.workload_ir.tasks + csp_module.items.workload_ir.tasks,
                channels=csp_module.items.workload_ir.channels,
                dependencies=wsp_module.items.workload_ir.dependencies,
                processes=csp_module.items.workload_ir.processes,
                routine={"kind": "composed", "entry": "run"},
            ),
            typed_items=wsp_module.items.typed_items + csp_module.items.typed_items,
        ),
        aspects=wsp_module.aspects,
        analyses=wsp_module.analyses,
        identity=wsp_module.identity,
        entrypoints=(ProgramEntrypoint(name="run", interpreter_id=NODE_PROGRAM_INTERPRETER_ID),),
        meta={
            "source_surface": "examples.ast_frontend_composability",
            "frontend_capture_modes": {
                "wsp": wsp_module.meta.get("frontend_capture"),
                "csp": csp_module.meta.get("frontend_capture"),
            },
            "active_dialects": [
                "htp.core",
                "htp.kernel",
                "htp.wsp",
                "htp.csp",
            ],
        },
    )


def run_demo() -> dict[str, Any]:
    composed = build_composed_module()
    report = composed.run(mode="sim")
    return {
        "wsp_capture": scheduled_tiles.to_program_module().meta.get("frontend_capture"),
        "csp_capture": streamed_tiles.to_program_module().meta.get("frontend_capture"),
        "task_ids": [task["task_id"] for task in scheduled_tiles.to_program()["wsp"]["workload"]["tasks"]],
        "process_ids": [process["task_id"] for process in streamed_tiles.to_program()["csp"]["processes"]],
        "composed_interpreters": report["interpreter_units"],
        "composed_task_graph": report["task_graph"]["graph"],
        "composed_process_graph": report["process_graph"]["graph"],
    }


def main() -> None:
    try:
        print(run_demo())
    except FrontendSyntaxError as exc:  # pragma: no cover - demo guard
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
