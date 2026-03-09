from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactContract:
    outputs: tuple[tuple[str, str], ...]

    @property
    def required_outputs(self) -> tuple[str, ...]:
        return tuple(path for _name, path in self.outputs)

    def as_manifest_outputs(self) -> dict[str, str]:
        return {name: path for name, path in self.outputs}

    def output_path(self, key: str) -> str | None:
        for name, path in self.outputs:
            if name == key:
                return path
        return None


@dataclass(frozen=True)
class BackendSolverDeclaration:
    backend: str
    variant: str
    hardware_profile: str
    target_capabilities: tuple[str, ...]
    supported_ops: tuple[str, ...]
    artifact_contract: ArtifactContract

    @property
    def required_outputs(self) -> tuple[str, ...]:
        return self.artifact_contract.required_outputs


__all__ = ["ArtifactContract", "BackendSolverDeclaration"]
