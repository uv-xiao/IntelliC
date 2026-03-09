from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htp import ark, bind, compile_program


@ark.build(target="nvgpu-blackwell", hardware=ark.blackwell())
def blackwell_cluster_gemm():
    """Blackwell cluster/TMA/WGMMA example using the Arknife-style HTP surface."""

    A = ark.tensor("A", dtype="bf16", shape=("M", "K"), role="input", memory="global")
    B = ark.tensor("B", dtype="bf16", shape=("K", "N"), role="input", memory="global")
    C = ark.tensor("C", dtype="f32", shape=("M", "N"), role="output", memory="global")
    AS = ark.tensor("AS", dtype="bf16", shape=("BM", "BK"), memory="shared")
    BS = ark.tensor("BS", dtype="bf16", shape=("BK", "BN"), memory="shared")
    TC = ark.tensor("TC", dtype="f32", shape=("BM", "BN"), memory="tensor")

    with ark.spatial("cluster", ark.axis("cluster_m", 2), ark.axis("cluster_n", 1)):
        with ark.pipeline(ark.axis("k_outer", 2), stages=2):
            ark.tma_load(AS, A, channel="cluster_pipe")
            ark.tma_load(BS, B, channel="cluster_pipe")
            ark.wgmma(TC, AS, BS, accum=TC, shape=(64, 128, 16), channel="cluster_pipe")
        ark.tma_store(C, TC, channel="store_pipe")
    return A, B, C


def compile_example(output_dir: Path | str) -> dict[str, Any]:
    package = compile_program(
        package_dir=Path(output_dir),
        target="nvgpu-blackwell",
        program=blackwell_cluster_gemm,
    )
    codegen_index_path = package.package_dir / "codegen" / "nvgpu" / "nvgpu_codegen.json"
    codegen_index = json.loads(codegen_index_path.read_text())
    return {
        "package_dir": package.package_dir.as_posix(),
        "target": {"backend": package.target.backend, "option": package.target.option},
        "manifest_path": (package.package_dir / "manifest.json").as_posix(),
        "instruction_plan": codegen_index["kernels"][0]["instruction_plan"],
        "hardware": codegen_index["arknife"]["hardware"],
    }


def replay_latest_stage(output_dir: Path | str) -> dict[str, Any]:
    package_dir = Path(output_dir)
    session = bind(package_dir).load(mode="sim")
    stage_id = session.manifest["stages"]["current"]
    result = session.replay(stage_id, trace="basic")
    return {
        "ok": result.ok,
        "stage_id": stage_id,
        "entry": result.entry,
        "diagnostics": result.diagnostics,
        "layout": result.result.get("layout", {}),
    }


def run_demo(output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    compile_summary = compile_example(output_path)
    replay_summary = replay_latest_stage(output_path)
    return {
        "example": "nvgpu_arknife_blackwell",
        "compile": compile_summary,
        "replay": replay_summary,
    }


def main() -> None:
    summary = run_demo(Path("artifacts") / "nvgpu_arknife_blackwell")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
