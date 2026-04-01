"""WSP-specific frontend lowering helpers and AST capture."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from htp.ir.core.nodes import dependency, item_ref, task, task_graph
from htp.ir.core.semantics import WorkloadDependency, WorkloadTask
from htp.ir.frontends import ASTFrontendVisitor, FrontendSyntaxError, handles, load_function_ast
from htp.ir.frontends.shared import FrontendWorkload, build_frontend_program_module


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
    spec: Any
    after: tuple[str, ...]


class WSPASTFrontendVisitor(ASTFrontendVisitor):
    """AST capture for nested-function WSP authored syntax."""

    def build_program(
        self,
        *,
        function: Any,
        kernel_spec: Any,
        target: dict[str, Any],
        entry: str,
    ) -> Any:
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
        from htp.wsp import WSPStageSpec, WSPStageStep, WSPTaskSpec

        decorator = node.decorator_list[0]
        if not isinstance(decorator, ast.Call):
            raise context.fail(node, "WSP nested task decorators must be calls")
        keyword_map = {item.arg: item.value for item in decorator.keywords if item.arg is not None}
        task_id = _literal_or_default(keyword_map.get("task_id"), default=node.name)
        kind = (
            "wsp_mainloop"
            if self.decorator_name(node) == "mainloop"
            else _literal_or_default(
                keyword_map.get("kind"),
                default="kernel_call",
            )
        )
        role = _literal_or_none(keyword_map.get("role"))
        task_args = tuple(
            _resolve_surface_value(item, context) for item in _sequence_values(keyword_map.get("args"))
        ) or _default_kernel_args(context.kernel_spec)
        stages: dict[str, list[WSPStageStep]] = {}
        for statement in node.body:
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
                continue
            stage_name, step = self.dispatch(statement, context)
            stages.setdefault(stage_name, []).append(step)
        attrs: dict[str, Any] = {}
        if role is not None:
            attrs["role"] = role
        schedule_payload = {
            name: _resolve_surface_value(value, context)
            for name, value in keyword_map.items()
            if name in {"tile", "bind", "pipeline", "resources", "specialize"}
        }
        if schedule_payload:
            attrs["schedule"] = schedule_payload
        if stages:
            attrs["stages"] = [WSPStageSpec(name=name, steps=list(values)) for name, values in stages.items()]
        after_names = tuple(
            _resolve_dependency_name(item) for item in _sequence_values(keyword_map.get("after"))
        )
        return _PendingWSPTask(
            function_name=node.name,
            spec=WSPTaskSpec(
                task_id=str(task_id),
                kind=str(kind),
                kernel=context.kernel_spec.name,
                args=tuple(str(item) for item in task_args),
                attrs=attrs,
            ),
            after=after_names,
        )

    @handles(ast.Expr, call="step")
    def build_stage_step(self, node: ast.Expr, context) -> tuple[str, Any]:
        from htp.wsp import WSPStageStep

        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "WSP step expression must be a call")
        call = node.value
        keyword_map = {item.arg: item.value for item in call.keywords if item.arg is not None}
        stage_name = _literal_or_default(keyword_map.pop("stage", None), default="steady")
        if not call.args:
            raise context.fail(node, "w.step(...) requires an op name")
        op_name = _resolve_surface_value(call.args[0], context)
        attrs = {name: _resolve_surface_value(value, context) for name, value in keyword_map.items()}
        return str(stage_name), WSPStageStep(op=str(op_name), attrs=attrs)


def build_wsp_ast_program_spec(
    *,
    function: Any,
    kernel_spec: Any,
    target: dict[str, Any],
    entry: str,
) -> Any:
    return WSPASTFrontendVisitor().build_program(
        function=function,
        kernel_spec=kernel_spec,
        target=target,
        entry=entry,
    )


def _aggregate_schedule(task_specs: tuple[Any, ...]) -> Any:
    from htp.wsp import WSPScheduleSpec

    for task_spec in task_specs:
        schedule_payload = task_spec.attrs.get("schedule")
        if schedule_payload:
            return WSPScheduleSpec.from_payload(schedule_payload)
    return WSPScheduleSpec()


def _build_wsp_ast_program_module(
    *,
    entry: str,
    target: dict[str, Any],
    kernel_spec: Any,
    payload: dict[str, Any],
    task_specs: tuple[Any, ...],
    dependency_specs: tuple[Any, ...],
) -> Any:
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
            attrs=_task_attrs_payload(task_spec.attrs),
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
    workload = wsp_frontend_workload(
        replace(
            payload_proxy_wsp(
                task_specs=task_specs, dependency_specs=dependency_specs, entry=entry, target=target
            ),
            schedule=_aggregate_schedule(task_specs),
        )
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


@dataclass(frozen=True)
class payload_proxy_wsp:
    task_specs: tuple[Any, ...]
    dependency_specs: tuple[Any, ...]
    entry: str
    target: dict[str, Any]
    schedule: Any | None = None

    @property
    def tasks(self) -> tuple[Any, ...]:
        return self.task_specs

    @property
    def channels(self) -> tuple[dict[str, Any], ...]:
        return ()

    @property
    def dependencies(self) -> tuple[Any, ...]:
        return self.dependency_specs


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


def _default_kernel_args(kernel_spec: Any) -> tuple[str, ...]:
    return tuple(argument.name for argument in kernel_spec.args if argument.name is not None)


def _sequence_values(node: ast.AST | None) -> tuple[ast.AST, ...]:
    if node is None:
        return ()
    if isinstance(node, (ast.List, ast.Tuple)):
        return tuple(node.elts)
    return (node,)


def _literal_or_default(node: ast.AST | None, *, default: Any) -> Any:
    if node is None:
        return default
    return ast.literal_eval(node)


def _literal_or_none(node: ast.AST | None) -> Any:
    if node is None:
        return None
    return ast.literal_eval(node)


def _resolve_dependency_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    raise FrontendSyntaxError("WSP dependency references must be nested task names")


def _resolve_surface_value(node: ast.AST, context) -> Any:
    path = ASTFrontendVisitor.attribute_path(node)
    if len(path) == 3 and path[1] == "args":
        return path[2]
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_resolve_surface_value(item, context) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            _resolve_surface_value(key, context): _resolve_surface_value(value, context)
            for key, value in zip(node.keys, node.values, strict=False)
        }
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError) as exc:
        raise context.fail(node, "Unsupported WSP frontend expression") from exc


def _surface_ref(*, node_id: str, name: str):
    from htp.ir.core.nodes import ref

    return ref(node_id, f"sym.{name}", name)


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


__all__ = ["WSPASTFrontendVisitor", "build_wsp_ast_program_spec", "wsp_frontend_workload"]
