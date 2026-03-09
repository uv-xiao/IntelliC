from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from htp.passes.registry import core_passes
from htp_ext.registry import active_extensions


def default_template(*, target: dict[str, str], required_outputs: tuple[str, ...]):
    from htp.solver import PipelineTemplate, _backend_declaration

    declaration = _backend_declaration(target)
    return PipelineTemplate(
        template_id="htp.default.v1",
        passes=tuple(item.contract for item in core_passes()),
        required_outputs=required_outputs,
        selection_cost=declaration.selection_cost,
    )


def extension_templates(
    *,
    program: Mapping[str, Any],
    required_outputs: tuple[str, ...],
):
    templates = []
    for extension in active_extensions(program):
        templates.extend(extension.pipeline_templates(program=program, required_outputs=required_outputs))
    return tuple(templates)


def registered_templates(*, program: Mapping[str, object], required_outputs: tuple[str, ...]):
    target = program.get("target", {})
    resolved_target = target if isinstance(target, dict) else {}
    return (
        default_template(target=resolved_target, required_outputs=required_outputs),
    ) + extension_templates(
        program=program,
        required_outputs=required_outputs,
    )


__all__ = ["default_template", "extension_templates", "registered_templates"]
