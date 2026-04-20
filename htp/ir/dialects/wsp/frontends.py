"""WSP-specific frontend lowering helpers and AST capture."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from htp.ir.core.nodes import dependency, item_ref, task, task_graph
from htp.ir.core.semantics import WorkloadDependency, WorkloadTask
from htp.ir.frontends import (
    ASTFrontendVisitor,
    default_kernel_args,
    handles,
    literal_or_default,
    literal_or_none,
    load_function_ast,
    ordered_resolved_values,
    resolve_name,
    resolve_surface_value,
    resolved_keyword_map,
    sequence_values,
    surface_ref,
)
from htp.ir.frontends.shared import FrontendWorkload, build_frontend_program_module

if TYPE_CHECKING:
    from htp.ir.program.module import ProgramModule
    from htp.kernel import KernelSpec
    from htp.wsp import WSPDependencySpec, WSPProgramSpec, WSPScheduleSpec, WSPStageStep, WSPTaskSpec


def wsp_frontend_workload(surface: object) -> FrontendWorkload:
    return FrontendWorkload(
        entry=surface.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=task_spec.task_id,
                kind=task_spec.kind,
                kernel=task_spec.kernel,
                args=task_spec.args,
                entity_id=f"{surface.entry}:{task_spec.task_id}",
                attrs=dict(task_spec.attrs),
            )
            for task_spec in surface.tasks
        ),
        channels=(),
        dependencies=tuple(
            WorkloadDependency(src=dependency_spec.src, dst=dependency_spec.dst)
            for dependency_spec in surface.dependencies
        ),
        routine={
            "kind": "wsp",
            "entry": surface.entry,
            "schedule": surface.schedule.to_payload(),
            "target": dict(surface.target),
        },
    )


@dataclass(frozen=True)
class _PendingWSPTask:
    function_name: str
    spec: WSPTaskSpec
    after: tuple[str, ...]


class WSPASTFrontendVisitor(ASTFrontendVisitor):
    """AST capture for nested-function WSP authored syntax."""

    def build_program(
        self,
        *,
        function: Any,
        kernel_spec: KernelSpec,
        target: dict[str, Any],
        entry: str,
    ) -> WSPProgramSpec | None:
        from htp.wsp import WSPDependencySpec, WSPProgramSpec

        function_ast = load_function_ast(function)
        nested_tasks = [
            node for node in function_ast.root.body if self.decorator_name(node) in {"task", "mainloop"}
        ]
        if not nested_tasks:
            return None
        context = self.build_context(
            frontend_id="htp.wsp.ast",
            dialect_id="htp.wsp",
            function_ast=function_ast,
            kernel_spec=kernel_spec,
            target=target,
            entry=entry,
        )
        pending = [self.dispatch(node, context) for node in nested_tasks]
        task_specs = tuple(item.spec for item in pending)
        id_by_function = {item.function_name: item.spec.task_id for item in pending}
        dependency_specs = tuple(
            WSPDependencySpec(src=id_by_function[source], dst=item.spec.task_id)
            for item in pending
            for source in item.after
        )
        schedule = _aggregate_schedule(task_specs)
        payload = _wsp_program_payload(
            entry=entry,
            target=target,
            kernel_spec=kernel_spec,
            tasks=task_specs,
            dependencies=dependency_specs,
            schedule=schedule,
        )
        module = _build_wsp_ast_program_module(
            entry=entry,
            target=target,
            kernel_spec=kernel_spec,
            payload=payload,
            task_specs=task_specs,
            dependency_specs=dependency_specs,
        )
        return WSPProgramSpec(
            entry=entry,
            target=target,
            kernel=kernel_spec,
            tasks=task_specs,
            channels=(),
            dependencies=dependency_specs,
            schedule=schedule,
            authored_program=payload,
            prebuilt_program_module=module,
        )

    @handles(ast.FunctionDef, decorator="task")
    @handles(ast.FunctionDef, decorator="mainloop")
    def build_task(self, node: ast.FunctionDef, context) -> _PendingWSPTask:
        from htp.wsp import WSPScheduleSpec, WSPStageSpec, WSPTaskSpec

        decorator = node.decorator_list[0]
        if not isinstance(decorator, ast.Call):
            raise context.fail(node, "WSP nested task decorators must be calls")
        keyword_map = {item.arg: item.value for item in decorator.keywords if item.arg is not None}
        task_id = literal_or_default(keyword_map.get("task_id"), default=node.name)
        kind = (
            "wsp_mainloop"
            if self.decorator_name(node) == "mainloop"
            else literal_or_default(
                keyword_map.get("kind"),
                default="kernel_call",
            )
        )
        role = literal_or_none(keyword_map.get("role"))
        task_args = ordered_resolved_values(
            sequence_values(keyword_map.get("args")), context
        ) or default_kernel_args(context.kernel_spec)
        stages: dict[str, list[WSPStageStep]] = {}
        for statement in node.body:
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
                continue
            emitted = self.dispatch(statement, context)
            for stage_name, step in _stage_emissions(emitted):
                stages.setdefault(stage_name, []).append(step)
        attrs: dict[str, Any] = {}
        schedule_payload = {
            name: resolve_surface_value(value, context)
            for name, value in keyword_map.items()
            if name in {"tile", "bind", "pipeline", "resources", "specialize"}
        }
        after_names = tuple(
            resolve_name(item, context, failure="WSP dependency references must be nested task names")
            for item in sequence_values(keyword_map.get("after"))
        )
        return _PendingWSPTask(
            function_name=node.name,
            spec=WSPTaskSpec(
                task_id=str(task_id),
                kind=str(kind),
                kernel=context.kernel_spec.name,
                args=tuple(str(item) for item in task_args),
                attrs=attrs,
                role=None if role is None else str(role),
                schedule=WSPScheduleSpec.from_payload(schedule_payload),
                stages=[WSPStageSpec(name=name, steps=list(values)) for name, values in stages.items()],
            ),
            after=after_names,
        )

    @handles(ast.With)
    def build_stage_block(self, node: ast.With, context) -> list[tuple[str, WSPStageStep]]:
        if len(node.items) != 1:
            raise context.fail(node, "WSP stage blocks accept one context manager")
        stage_name = _wsp_stage_name(node.items[0].context_expr, context)
        previous_stage = context.emitted.get("wsp_stage")
        context.emitted["wsp_stage"] = stage_name
        emitted: list[tuple[str, WSPStageStep]] = []
        try:
            for statement in node.body:
                if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
                    continue
                emitted.extend(_stage_emissions(self.dispatch(statement, context)))
        finally:
            if previous_stage is None:
                context.emitted.pop("wsp_stage", None)
            else:
                context.emitted["wsp_stage"] = previous_stage
        return emitted

    @handles(ast.Expr, call="step")
    def build_stage_step(self, node: ast.Expr, context) -> tuple[str, WSPStageStep]:
        from htp.wsp import WSPStageStep

        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "WSP step expression must be a call")
        call = node.value
        keyword_map = {item.arg: item.value for item in call.keywords if item.arg is not None}
        stage_name = literal_or_default(keyword_map.pop("stage", None), default="steady")
        if not call.args:
            raise context.fail(node, "w.step(...) requires an op name")
        op_name = resolve_surface_value(call.args[0], context)
        attrs = {name: resolve_surface_value(value, context) for name, value in keyword_map.items()}
        return str(stage_name), WSPStageStep(op=str(op_name), attrs=attrs)

    @handles(ast.Expr)
    def build_intrinsic_stage_step(self, node: ast.Expr, context) -> tuple[str, WSPStageStep]:
        from htp.wsp import WSPStageStep

        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "WSP stage expression must be a call")
        op_name = self.call_name(node)
        if op_name in {None, "task", "mainloop", "step", "stage", "prologue", "steady", "epilogue"}:
            raise context.fail(node, "Unsupported WSP stage expression")
        attrs = resolved_keyword_map(node.value, context)
        positional = [resolve_surface_value(item, context) for item in node.value.args]
        if positional:
            attrs["args"] = positional
        return str(context.emitted.get("wsp_stage", "steady")), WSPStageStep(op=str(op_name), attrs=attrs)


def build_wsp_ast_program_spec(
    *,
    function: Any,
    kernel_spec: KernelSpec,
    target: dict[str, Any],
    entry: str,
) -> WSPProgramSpec | None:
    return WSPASTFrontendVisitor().build_program(
        function=function,
        kernel_spec=kernel_spec,
        target=target,
        entry=entry,
    )


def _aggregate_schedule(task_specs: tuple[WSPTaskSpec, ...]) -> WSPScheduleSpec:
    from htp.wsp import WSPScheduleSpec

    for task_spec in task_specs:
        if task_spec.schedule is not None and task_spec.schedule.has_values():
            return task_spec.schedule
    return WSPScheduleSpec()


def _build_wsp_ast_program_module(
    *,
    entry: str,
    target: dict[str, Any],
    kernel_spec: KernelSpec,
    payload: dict[str, Any],
    task_specs: tuple[WSPTaskSpec, ...],
    dependency_specs: tuple[WSPDependencySpec, ...],
) -> ProgramModule:
    kernel_module = kernel_spec.to_program_module()
    task_handle = item_ref(
        f"itemref.{entry}.kernel",
        f"item.{kernel_spec.name}",
        kernel_spec.name,
    )
    task_nodes = tuple(
        task(
            f"task.{entry}.{task_spec.task_id}",
            task_spec.task_id,
            kernel=task_handle,
            args=tuple(
                _surface_ref(
                    node_id=f"taskarg.{entry}.{task_spec.task_id}.{index}",
                    name=arg,
                )
                for index, arg in enumerate(task_spec.args)
            ),
            attrs=_task_attrs_payload(task_spec.semantic_attrs()),
        )
        for task_spec in task_specs
    )
    graph = task_graph(
        f"item.task_graph.{entry}",
        entry,
        tasks=task_nodes,
        dependencies=tuple(
            dependency(
                f"dep.{entry}.{index}",
                src_task=dependency_spec.src,
                dst_task=dependency_spec.dst,
            )
            for index, dependency_spec in enumerate(dependency_specs)
        ),
    )
    workload = FrontendWorkload(
        entry=entry,
        tasks=tuple(
            WorkloadTask(
                task_id=task_spec.task_id,
                kind=task_spec.kind,
                kernel=task_spec.kernel,
                args=task_spec.args,
                entity_id=f"{entry}:{task_spec.task_id}",
                attrs=task_spec.semantic_attrs(),
            )
            for task_spec in task_specs
        ),
        dependencies=tuple(
            WorkloadDependency(src=dependency_spec.src, dst=dependency_spec.dst)
            for dependency_spec in dependency_specs
        ),
        routine={
            "kind": "wsp",
            "entry": entry,
            "schedule": _aggregate_schedule(task_specs).to_payload(),
            "target": dict(target),
        },
    )
    module = build_frontend_program_module(
        kernel_module=kernel_module,
        authored_program=payload,
        workload=workload,
        source_surface="htp.wsp.WSPProgramSpec",
        active_dialects=("htp.core", "htp.kernel", "htp.wsp"),
        typed_items=(graph,),
    )
    return replace(module, meta={**module.meta, "frontend_capture": "ast"})


def _wsp_program_payload(
    *,
    entry: str,
    target: dict[str, Any],
    kernel_spec: Any,
    tasks: tuple[Any, ...],
    dependencies: tuple[Any, ...],
    schedule: Any,
) -> dict[str, Any]:
    return {
        "entry": entry,
        "target": dict(target),
        "kernel": kernel_spec.to_payload(),
        "wsp": {
            "workload": {
                "entry": entry,
                "tasks": [task_spec.to_payload() for task_spec in tasks],
                "channels": [],
                "dependencies": [dependency_spec.to_payload() for dependency_spec in dependencies],
            },
            "schedule": schedule.to_payload(),
        },
    }


def _surface_ref(*, node_id: str, name: str):
    return surface_ref(node_id=node_id, name=name)


def _task_attrs_payload(attrs: Mapping[str, Any]) -> dict[str, Any]:
    from htp.ir.dialects.wsp import stages_to_payload

    payload: dict[str, Any] = {}
    for key, value in attrs.items():
        if key == "stages":
            payload[key] = stages_to_payload(tuple(value))
        elif isinstance(value, Mapping):
            payload[key] = dict(value)
        else:
            payload[key] = value
    return payload


def _stage_emissions(emitted: object) -> list[tuple[str, WSPStageStep]]:
    from htp.wsp import WSPStageStep

    if isinstance(emitted, tuple) and len(emitted) == 2 and isinstance(emitted[1], WSPStageStep):
        return [(str(emitted[0]), emitted[1])]
    if isinstance(emitted, list):
        return [item for item in emitted if isinstance(item, tuple) and len(item) == 2]
    return []


def _wsp_stage_name(node: ast.AST, context) -> str:
    if not isinstance(node, ast.Call):
        raise context.fail(
            node, "WSP stage block must call w.stage(...), w.prologue(), w.steady(), or w.epilogue()"
        )
    call_name = WSPASTFrontendVisitor.call_name(node)
    if call_name in {"prologue", "steady", "epilogue"}:
        return call_name
    if call_name == "stage" and node.args:
        return str(resolve_surface_value(node.args[0], context))
    raise context.fail(node, "Unsupported WSP stage block")


__all__ = ["WSPASTFrontendVisitor", "build_wsp_ast_program_spec", "wsp_frontend_workload"]
