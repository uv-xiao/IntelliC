from __future__ import annotations

from collections.abc import Mapping, Sequence


class ArtifactValidationError(ValueError):
    """Raised when staged artifact metadata violates the v1 contract."""


def validate_runnable_py(
    *,
    status: str,
    modes: Sequence[str],
    has_stubs: bool,
) -> None:
    if status not in {"preserves", "stubbed"}:
        raise ArtifactValidationError(f"Unsupported runnable_py status: {status}")
    if "sim" not in modes:
        raise ArtifactValidationError("Stage runnable_py.modes must include 'sim'")
    if status == "stubbed" and not has_stubs:
        raise ArtifactValidationError("Stubbed stages must emit replay/stubs.json")


def validate_manifest_graph(*, current_stage: str, stages: Sequence[Mapping[str, object]]) -> None:
    stage_ids = [str(stage["id"]) for stage in stages]
    if current_stage not in stage_ids:
        raise ArtifactValidationError(
            f"Current stage {current_stage!r} is not present in the manifest stage graph"
        )


__all__ = [
    "ArtifactValidationError",
    "validate_manifest_graph",
    "validate_runnable_py",
]
