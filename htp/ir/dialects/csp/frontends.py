"""CSP-specific frontend lowering helpers and AST capture."""

from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from typing import Any

from htp.ir.core.nodes import channel, item_ref, process, process_graph, process_step
from htp.ir.core.semantics import WorkloadChannel, WorkloadProcess, WorkloadProcessStep, WorkloadTask
from htp.ir.frontends import ASTFrontendVisitor, handles, load_function_ast
from htp.ir.frontends.shared import FrontendWorkload, build_frontend_program_module


def csp_frontend_workload(surface: object) -> FrontendWorkload:
    return FrontendWorkload(
        entry=surface.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=process_spec.task_id,
                kind="process",
                kernel=process_spec.kernel,
                args=process_spec.args,
                entity_id=f"{surface.entry}:{process_spec.task_id}",
                attrs={
                    "name": process_spec.name,
                    **({"role": process_spec.role} if process_spec.role is not None else {}),
                },
            )
            for process_spec in surface.processes
        ),
        channels=tuple(
            WorkloadChannel(
                name=channel_ref.name,
                dtype=channel_ref.dtype,
                capacity=channel_ref.capacity,
                protocol=channel_ref.protocol,
            )
            for channel_ref in surface.channels
        ),
        dependencies=(),
        processes=tuple(
            WorkloadProcess(
                name=process_spec.name,
                task_id=process_spec.task_id,
                kernel=process_spec.kernel,
                args=process_spec.args,
                role=process_spec.role,
                steps=tuple(
                    WorkloadProcessStep(kind=step.kind, attrs=dict(step.attrs))
                    for step in process_spec.steps
                ),
            )
            for process_spec in surface.processes
        ),
        routine={"kind": "csp", "entry": surface.entry, "target": dict(surface.target)},
    )


@dataclass(frozen=True)
class _PendingProcess:
    spec: Any


class CSPASTFrontendVisitor(ASTFrontendVisitor):
    """AST capture for nested-function CSP authored syntax."""

    def build_program(
        self,
        *,
        function: Any,
        kernel_spec: Any,
        target: dict[str, Any],
        entry: str,
    ) -> Any:
        from htp.csp import CSPProgramSpec

        function_ast = load_function_ast(function)
        nested_processes = [node for node in function_ast.root.body if self.decorator_name(node) == "process"]
        if not nested_processes:
            return None
        context = self.build_context(
            frontend_id="htp.csp.ast",
            dialect_id="htp.csp",
            function_ast=function_ast,
            kernel_spec=kernel_spec,
            target=target,
            entry=entry,
        )
        self._collect_channels(function_ast.root.body, context)
        process_specs = tuple(self.dispatch(node, context).spec for node in nested_processes)
        payload = _csp_program_payload(
            entry=entry,
            target=target,
            kernel_spec=kernel_spec,
            channels=tuple(context.symbols.values()),
            processes=process_specs,
        )
        module = _build_csp_ast_program_module(
            entry=entry,
            target=target,
            kernel_spec=kernel_spec,
            payload=payload,
            channels=tuple(context.symbols.values()),
            process_specs=process_specs,
        )
        return CSPProgramSpec(
            entry=entry,
            target=target,
            kernel=kernel_spec,
            channels=tuple(context.symbols.values()),
            processes=process_specs,
            authored_program=payload,
            prebuilt_program_module=module,
        )

    def _collect_channels(self, statements: list[ast.stmt], context) -> None:
        for statement in statements:
            if not isinstance(statement, ast.Assign) or self.call_name(statement) not in {"fifo", "channel"}:
                continue
            self.dispatch(statement, context)

    @handles(ast.Assign, call="fifo")
    @handles(ast.Assign, call="channel")
    def build_channel(self, node: ast.Assign, context) -> None:
        from htp.csp import ChannelRef

        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise context.fail(node, "CSP channel declarations require one simple name target")
        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "CSP channel declarations must call c.fifo(...) or c.channel(...)")
        call = node.value
        keyword_map = {item.arg: item.value for item in call.keywords if item.arg is not None}
        if self.call_name(call) == "fifo":
            protocol = "fifo"
        else:
            protocol = str(_resolve_surface_value(keyword_map.get("protocol"), context))
        context.symbols[node.targets[0].id] = ChannelRef(
            name=node.targets[0].id,
            dtype=str(_resolve_surface_value(keyword_map["dtype"], context)),
            capacity=int(_resolve_surface_value(keyword_map["capacity"], context)),
            protocol=protocol,
        )

    @handles(ast.FunctionDef, decorator="process")
    def build_process(self, node: ast.FunctionDef, context) -> _PendingProcess:
        from htp.csp import CSPProcessSpec

        decorator = node.decorator_list[0]
        if not isinstance(decorator, ast.Call):
            raise context.fail(node, "CSP nested process decorators must be calls")
        keyword_map = {item.arg: item.value for item in decorator.keywords if item.arg is not None}
        process_args = tuple(
            _resolve_surface_value(item, context) for item in _sequence_values(keyword_map.get("args"))
        ) or _default_kernel_args(context.kernel_spec)
        role = _resolve_surface_value(keyword_map.get("role"), context) if "role" in keyword_map else None
        steps = []
        context.locals = {}
        for statement in node.body:
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
                continue
            emitted = self.dispatch(statement, context)
            if emitted is not None:
                steps.append(emitted)
        return _PendingProcess(
            spec=CSPProcessSpec(
                name=node.name,
                task_id=str(_resolve_surface_value(keyword_map.get("task_id"), context) or node.name),
                kernel=context.kernel_spec.name,
                args=tuple(str(item) for item in process_args),
                steps=steps,
                role=None if role is None else str(role),
            )
        )

    @handles(ast.Assign, call="get")
    def build_get_step(self, node: ast.Assign, context):
        from htp.ir.dialects.csp import CSPProcessStep

        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "CSP get step must be a call")
        call = node.value
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise context.fail(node, "CSP get step requires one simple binding target")
        channel_name = _resolve_channel_name(call.args[0], context)
        count = _keyword_or_default(call, "count", 1, context)
        context.locals[node.targets[0].id] = node.targets[0].id
        return CSPProcessStep(kind="get", attrs={"channel": channel_name, "count": count})

    @handles(ast.Expr, call="put")
    def build_put_step(self, node: ast.Expr, context):
        from htp.ir.dialects.csp import CSPProcessStep

        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "CSP put step must be a call")
        call = node.value
        channel_name = _resolve_channel_name(call.args[0], context)
        count = _keyword_or_default(call, "count", 1, context)
        return CSPProcessStep(kind="put", attrs={"channel": channel_name, "count": count})

    @handles(ast.Expr, call="compute")
    def build_compute_step(self, node: ast.Expr, context):
        from htp.ir.dialects.csp import CSPProcessStep

        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "CSP compute step must be a call")
        call = node.value
        if not call.args:
            raise context.fail(node, "c.compute(...) requires a step name")
        attrs = {"name": _resolve_surface_value(call.args[0], context)}
        attrs.update(_resolved_keyword_map(call, context))
        return CSPProcessStep(kind="compute", attrs=attrs)

    @handles(ast.Expr, call="compute_step")
    def build_compute_op_step(self, node: ast.Expr, context):
        from htp.ir.dialects.csp import CSPProcessStep

        if not isinstance(node.value, ast.Call):
            raise context.fail(node, "CSP compute_step must be a call")
        call = node.value
        if not call.args:
            raise context.fail(node, "c.compute_step(...) requires an op name")
        attrs = {"op": _resolve_surface_value(call.args[0], context)}
        attrs.update(_resolved_keyword_map(call, context))
        return CSPProcessStep(kind="compute", attrs=attrs)


def build_csp_ast_program_spec(
    *,
    function: Any,
    kernel_spec: Any,
    target: dict[str, Any],
    entry: str,
) -> Any:
    return CSPASTFrontendVisitor().build_program(
        function=function,
        kernel_spec=kernel_spec,
        target=target,
        entry=entry,
    )


def _build_csp_ast_program_module(
    *,
    entry: str,
    target: dict[str, Any],
    kernel_spec: Any,
    payload: dict[str, Any],
    channels: tuple[Any, ...],
    process_specs: tuple[Any, ...],
) -> Any:
    kernel_module = kernel_spec.to_program_module()
    kernel_handle = item_ref(
        f"itemref.{entry}.kernel",
        f"item.{kernel_spec.name}",
        kernel_spec.name,
    )
    channel_nodes = tuple(
        channel(
            f"item.channel.{entry}.{channel_ref.name}",
            channel_ref.name,
            channel_id=f"chan.{entry}.{channel_ref.name}",
            dtype=channel_ref.dtype,
            capacity=channel_ref.capacity,
            protocol=channel_ref.protocol,
        )
        for channel_ref in channels
    )
    channel_ids = {channel_ref.name: f"chan.{entry}.{channel_ref.name}" for channel_ref in channels}
    process_nodes = tuple(
        process(
            f"process.{entry}.{process_spec.task_id}",
            process_spec.task_id,
            kernel=kernel_handle,
            args=tuple(
                _surface_ref(
                    node_id=f"processarg.{entry}.{process_spec.task_id}.{index}",
                    name=arg,
                )
                for index, arg in enumerate(process_spec.args)
            ),
            steps=tuple(
                process_step(
                    f"processstep.{entry}.{process_spec.task_id}.{index}",
                    kind=step.kind,
                    channel_id=channel_ids.get(step.attrs.get("channel"))
                    if step.attrs.get("channel")
                    else None,
                    attrs=dict(step.attrs),
                )
                for index, step in enumerate(process_spec.steps)
            ),
            attrs={"name": process_spec.name, **({"role": process_spec.role} if process_spec.role else {})},
        )
        for process_spec in process_specs
    )
    graph = process_graph(
        f"item.process_graph.{entry}",
        entry,
        channels=channel_nodes,
        processes=process_nodes,
    )
    workload = csp_frontend_workload(
        _SurfaceCSPProxy(
            entry=entry,
            target=target,
            channels=channels,
            processes=process_specs,
        )
    )
    module = build_frontend_program_module(
        kernel_module=kernel_module,
        authored_program=payload,
        workload=workload,
        source_surface="htp.csp.CSPProgramSpec",
        active_dialects=("htp.core", "htp.kernel", "htp.csp"),
        typed_items=(graph,),
    )
    return replace(module, meta={**module.meta, "frontend_capture": "ast"})


@dataclass(frozen=True)
class _SurfaceCSPProxy:
    entry: str
    target: dict[str, Any]
    channels: tuple[Any, ...]
    processes: tuple[Any, ...]


def _csp_program_payload(
    *,
    entry: str,
    target: dict[str, Any],
    kernel_spec: Any,
    channels: tuple[Any, ...],
    processes: tuple[Any, ...],
) -> dict[str, Any]:
    return {
        "entry": entry,
        "target": dict(target),
        "kernel": kernel_spec.to_payload(),
        "csp": {
            "channels": [channel_ref.to_payload() for channel_ref in channels],
            "processes": [process_spec.to_payload() for process_spec in processes],
        },
    }


def _default_kernel_args(kernel_spec: Any) -> tuple[str, ...]:
    return tuple(argument.name for argument in kernel_spec.args if argument.name is not None)


def _sequence_values(node: ast.AST | None) -> tuple[ast.AST, ...]:
    if node is None:
        return ()
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(node.elts)
    return (node,)


def _resolve_channel_name(node: ast.AST, context) -> str:
    value = _resolve_surface_value(node, context)
    return str(getattr(value, "name", value))


def _resolved_keyword_map(call: ast.Call, context) -> dict[str, Any]:
    return {
        item.arg: _resolve_surface_value(item.value, context)
        for item in call.keywords
        if item.arg is not None
    }


def _keyword_or_default(call: ast.Call, key: str, default: Any, context) -> Any:
    for item in call.keywords:
        if item.arg == key:
            return _resolve_surface_value(item.value, context)
    return default


def _resolve_surface_value(node: ast.AST | None, context) -> Any:
    if node is None:
        return None
    path = ASTFrontendVisitor.attribute_path(node)
    if len(path) == 3 and path[1] == "args":
        return path[2]
    if isinstance(node, ast.Name):
        if node.id in context.symbols:
            return context.symbols[node.id]
        if node.id in context.locals:
            return context.locals[node.id]
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
        raise context.fail(node, "Unsupported CSP frontend expression") from exc


def _surface_ref(*, node_id: str, name: str):
    from htp.ir.core.nodes import ref

    return ref(node_id, f"sym.{name}", name)


__all__ = ["CSPASTFrontendVisitor", "build_csp_ast_program_spec", "csp_frontend_workload"]
