from __future__ import annotations

from pathlib import PurePosixPath

from htp.backends.declarations import ArtifactContract, BackendSolverDeclaration

AIE_PROJECT_DIR = PurePosixPath("codegen/aie")
AIE_TOOLCHAIN_PATH = (AIE_PROJECT_DIR / "toolchain.json").as_posix()


def declaration_for(profile: str | None = None) -> BackendSolverDeclaration:
    resolved_profile = "xdna2-npu1" if not profile else profile
    return BackendSolverDeclaration(
        backend="aie",
        variant="mlir-aie",
        hardware_profile=f"amd-xdna2:{resolved_profile}",
        target_capabilities=(
            "Target.aie.TileGrid@1",
            "Target.aie.MemorySpace.l2@1",
            "Target.aie.MemorySpace.stream@1",
        ),
        supported_ops=("elementwise_binary", "channel_send", "channel_recv"),
        artifact_contract=ArtifactContract(
            outputs=(
                ("aie_codegen_index", (AIE_PROJECT_DIR / "aie_codegen.json").as_posix()),
                ("toolchain_manifest", AIE_TOOLCHAIN_PATH),
            )
        ),
    )


__all__ = ["AIE_TOOLCHAIN_PATH", "declaration_for"]
