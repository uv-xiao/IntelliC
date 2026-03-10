from __future__ import annotations

from pathlib import PurePosixPath

from htp.backends.declarations import ArtifactContract, BackendSolverDeclaration

CPU_REF_PROJECT_DIR = PurePosixPath("codegen/cpu_ref")
CPU_REF_TOOLCHAIN_PATH = PurePosixPath("build/toolchain.json")


def declaration_for(_variant: str | None = None) -> BackendSolverDeclaration:
    return BackendSolverDeclaration(
        backend="cpu_ref",
        variant="python",
        hardware_profile="host:python:numpy",
        target_capabilities=(
            "Target.cpu_ref.HostPython@1",
            "Target.cpu_ref.Numpy@1",
        ),
        supported_ops=(
            "elementwise_binary",
            "elementwise_unary",
            "matmul",
            "reduction_sum",
            "broadcast",
            "transpose",
            "cast",
        ),
        selection_cost=15,
        artifact_contract=ArtifactContract(
            outputs=(
                ("cpu_ref_codegen_index", (CPU_REF_PROJECT_DIR / "cpu_ref_codegen.json").as_posix()),
                ("toolchain_manifest", CPU_REF_TOOLCHAIN_PATH.as_posix()),
            )
        ),
    )


__all__ = ["CPU_REF_PROJECT_DIR", "CPU_REF_TOOLCHAIN_PATH", "declaration_for"]
