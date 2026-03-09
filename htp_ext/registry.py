from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtensionRegistration:
    extension_id: str
    registered_passes: Callable[[], tuple[Any, ...]]
    pipeline_templates: Callable[[Mapping[str, Any], tuple[str, ...]], tuple[Any, ...]]
    solver_result: Callable[[Mapping[str, Any]], dict[str, Any]]


def requested_extension_ids(program: Mapping[str, Any]) -> tuple[str, ...]:
    extensions = program.get("extensions", {})
    if not isinstance(extensions, Mapping):
        return ()
    requested = extensions.get("requested", ())
    if isinstance(requested, (str, bytes)) or not isinstance(requested, tuple | list):
        return ()
    return tuple(str(item) for item in requested)


def _registry() -> dict[str, ExtensionRegistration]:
    from htp_ext.mlir_cse.island import (
        EXTENSION_ID as MLIR_CSE_EXTENSION_ID,
    )
    from htp_ext.mlir_cse.island import (
        extension_solver_result as mlir_cse_solver_result,
    )
    from htp_ext.mlir_cse.island import (
        pipeline_templates as mlir_cse_templates,
    )
    from htp_ext.mlir_cse.island import (
        registered_passes as mlir_cse_registered_passes,
    )

    return {
        MLIR_CSE_EXTENSION_ID: ExtensionRegistration(
            extension_id=MLIR_CSE_EXTENSION_ID,
            registered_passes=mlir_cse_registered_passes,
            pipeline_templates=mlir_cse_templates,
            solver_result=mlir_cse_solver_result,
        ),
    }


def active_extensions(program: Mapping[str, Any]) -> tuple[ExtensionRegistration, ...]:
    registry = _registry()
    return tuple(
        registry[extension_id]
        for extension_id in requested_extension_ids(program)
        if extension_id in registry
    )


def extension_results(program: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        registration.extension_id: registration.solver_result(program)
        for registration in active_extensions(program)
    }


__all__ = [
    "ExtensionRegistration",
    "active_extensions",
    "extension_results",
    "requested_extension_ids",
]
