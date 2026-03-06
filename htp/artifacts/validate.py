from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


class ArtifactValidationError(ValueError):
    """Raised when staged artifact metadata violates the v1 contract."""


_SAFE_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ALLOWED_RUNNABLE_MODES = {"sim", "device"}


def validate_path_component(*, field_name: str, value: str) -> None:
    if not value or not _SAFE_PATH_COMPONENT_RE.fullmatch(value) or value == "..":
        raise ArtifactValidationError(
            f"{field_name} must be a package-local basename without separators or '..'"
        )


def validate_runnable_py(
    *,
    status: str,
    modes: Sequence[str],
    has_stubs: bool,
) -> None:
    if status not in {"preserves", "stubbed"}:
        raise ArtifactValidationError(f"Unsupported runnable_py status: {status}")
    if any(mode not in _ALLOWED_RUNNABLE_MODES for mode in modes):
        raise ArtifactValidationError("Stage runnable_py.modes must be a subset of {'sim', 'device'}")
    if "sim" not in modes:
        raise ArtifactValidationError("Stage runnable_py.modes must include 'sim'")
    if status == "stubbed" and not has_stubs:
        raise ArtifactValidationError("Stubbed stages must emit replay/stubs.json")


def validate_manifest_graph(*, current_stage: str, stages: Sequence[Mapping[str, object]]) -> None:
    stage_ids = [str(stage["id"]) for stage in stages]
    if len(stage_ids) != len(set(stage_ids)):
        raise ArtifactValidationError("Duplicate stage ids are not allowed in the manifest stage graph")
    if current_stage not in stage_ids:
        raise ArtifactValidationError(
            f"Current stage {current_stage!r} is not present in the manifest stage graph"
        )


__all__ = [
    "ArtifactValidationError",
    "validate_manifest_graph",
    "validate_path_component",
    "validate_runnable_py",
]
