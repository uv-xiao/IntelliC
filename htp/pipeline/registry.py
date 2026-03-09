from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from htp.passes.registry import core_passes
from htp_ext.registry import active_extensions


def default_template(*, target: dict[str, str], required_outputs: tuple[str, ...]):
    from htp.solver import PipelineTemplate

    del target
    return PipelineTemplate(
        template_id="htp.default.v1",
        passes=tuple(item.contract for item in core_passes()),
        required_outputs=required_outputs,
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
    return (default_template(target={}, required_outputs=required_outputs),) + extension_templates(
        program=program,
        required_outputs=required_outputs,
    )


__all__ = ["default_template", "extension_templates", "registered_templates"]
