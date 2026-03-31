"""WSP authoring helpers and builder surface.

This module keeps the original payload-builder helpers for low-level contract
tests, but the primary public surface is now the decorator/builder path:

    @wsp.program(target="nvgpu-ampere", kernel=my_kernel)
    def my_workload(w):
        (
            w.launch(my_kernel, "A", "B", "C", "M", "N", "K", task_id="main")
            .tile(block=(128, 128, 32))
            .bind(grid="block", lane="warp")
            .pipeline(depth=3, buffering="double")
            .resources(num_warps=8)
            .specialize(operator="matmul")
        )

That keeps WSP authoring in normal Python while preserving the existing
`to_program()` contract shape.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from inspect import signature
from typing import Any

from htp.compiler import parse_target
from htp.ir.frontend import FrontendWorkload, build_frontend_program_module, kernel_spec_from_payload
from htp.ir.module import ProgramModule
from htp.ir.semantics import WorkloadTask
from htp.kernel import KernelSpec, KernelValue


def task(
    kernel: KernelSpec | str,
    *args: str | KernelValue,
    task_id: str | None = None,
    kind: str = "kernel_call",
    attrs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    kernel_name = kernel.name if isinstance(kernel, KernelSpec) else str(kernel)
    resolved_task_id = task_id or f"{kernel_name}_0"
    payload = {
        "task_id": resolved_task_id,
        "kind": kind,
        "kernel": kernel_name,
        "args": [_ref(arg) for arg in args],
    }
    if attrs:
        payload["attrs"] = dict(attrs)
    return payload


def workload(
    *,
    entry: str,
    tasks: Sequence[Mapping[str, Any]],
    channels: Sequence[Mapping[str, Any]] = (),
    dependencies: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "entry": entry,
        "tasks": [dict(item) for item in tasks],
        "channels": [dict(item) for item in channels],
        "dependencies": [dict(item) for item in dependencies],
    }


def tile(*, block: tuple[int, int, int] | list[int]) -> dict[str, Any]:
    return {"block": list(block)}


def bind(*, grid: str | None = None, lane: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if grid is not None:
        payload["grid"] = grid
    if lane is not None:
        payload["lane"] = lane
    return payload


def pipeline(*, depth: int, buffering: str = "double") -> dict[str, Any]:
    return {"depth": depth, "buffering": buffering}


def resources(*, num_warps: int) -> dict[str, Any]:
    return {"num_warps": num_warps}


def specialize(*, operator: str, **attrs: Any) -> dict[str, Any]:
    return {"operator": operator, **dict(attrs)}


def schedule(
    *,
    tile: Mapping[str, Any] | None = None,
    bind: Mapping[str, Any] | None = None,
    pipeline: Mapping[str, Any] | None = None,
    resources: Mapping[str, Any] | None = None,
    specialize: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "tile": dict(tile or {}),
        "bind": dict(bind or {}),
        "pipeline": dict(pipeline or {}),
        "resources": dict(resources or {}),
        "specialize": dict(specialize or {}),
    }


@dataclass(frozen=True)
class WSPProgramSpec:
    """Frozen WSP program surface that compiles through `to_program()`."""

    entry: str
    target: dict[str, Any]
    kernel: dict[str, Any]
    workload: dict[str, Any]
    schedule: dict[str, Any]

    def to_program(self) -> dict[str, Any]:
        return {
            "entry": self.entry,
            "target": dict(self.target),
            "kernel": dict(self.kernel),
            "wsp": {
                "workload": {
                    "entry": str(self.workload["entry"]),
                    "tasks": [dict(item) for item in self.workload.get("tasks", ())],
                    "channels": [dict(item) for item in self.workload.get("channels", ())],
                    "dependencies": [dict(item) for item in self.workload.get("dependencies", ())],
                },
                "schedule": {
                    key: dict(value) if isinstance(value, Mapping) else value
                    for key, value in self.schedule.items()
                },
            },
        }

    def to_program_module(self) -> ProgramModule:
        return build_wsp_program_module(self)


def build_wsp_program_module(spec: WSPProgramSpec) -> ProgramModule:
    authored_program = spec.to_program()
    kernel_spec = kernel_spec_from_payload(spec.kernel)
    kernel_module = kernel_spec.to_program_module()
    workload = FrontendWorkload(
        entry=spec.entry,
        tasks=tuple(
            WorkloadTask(
                task_id=str(task["task_id"]),
                kind=str(task["kind"]),
                kernel=str(task["kernel"]),
                args=tuple(str(arg) for arg in task.get("args", ())),
                entity_id=f"{spec.entry}:{task['task_id']}",
                attrs=dict(task.get("attrs", {})),
            )
            for task in spec.workload.get("tasks", ())
        ),
        channels=tuple(dict(item) for item in spec.workload.get("channels", ())),
        dependencies=tuple(dict(item) for item in spec.workload.get("dependencies", ())),
        routine={
            "kind": "wsp",
            "entry": spec.entry,
            "schedule": {key: dict(value) for key, value in spec.schedule.items()},
            "target": dict(spec.target),
        },
    )
    return build_frontend_program_module(
        kernel_module=kernel_module,
        authored_program=authored_program,
        workload=workload,
        source_surface="htp.wsp.WSPProgramSpec",
        active_dialects=("htp.core", "htp.kernel", "htp.wsp"),
    )


class WSPBoundArgs:
    """Named kernel-argument bindings exposed to WSP authored workloads."""

    def __init__(self, values: Mapping[str, KernelValue]):
        self._values = dict(values)

    def __getattr__(self, name: str) -> KernelValue:
        try:
            return self._values[name]
        except KeyError as exc:  # pragma: no cover - defensive surface
            raise AttributeError(name) from exc

    def ordered(self, names: Sequence[str] | None = None) -> tuple[KernelValue, ...]:
        if names is None:
            return tuple(self._values[name] for name in self._values)
        return tuple(self._values[name] for name in names)


@dataclass
class WSPBuilder:
    """Mutable builder used by `@wsp.program(...)` decorator mode."""

    entry: str
    kernel_spec: KernelSpec
    target: dict[str, Any]
    tasks: list[dict[str, Any]] = field(default_factory=list)
    channels: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    schedule_state: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "tile": {},
            "bind": {},
            "pipeline": {},
            "resources": {},
            "specialize": {},
        }
    )
    _schedule_defaults_stack: list[dict[str, dict[str, Any]]] = field(default_factory=list)
    args: WSPBoundArgs = field(init=False)

    def __post_init__(self) -> None:
        bound_values = {
            argument.name: KernelValue(
                name=argument.name,
                dtype=argument.dtype,
                shape=argument.shape,
                kind=argument.kind,
                role=argument.role,
                memory_space=argument.memory_space,
                axis_layout=argument.axis_layout,
                distribution=argument.distribution,
                attrs=None if argument.attrs is None else dict(argument.attrs),
            )
            for argument in self.kernel_spec.args
            if argument.name is not None
        }
        self.args = WSPBoundArgs(bound_values)

    def launch(
        self,
        kernel: KernelSpec | str | None = None,
        *args: str | KernelValue,
        task_id: str | None = None,
        kind: str = "kernel_call",
    ) -> WSPTaskBuilder:
        resolved_kernel = self.kernel_spec if kernel is None else kernel
        resolved_args = args or self._default_args_for(resolved_kernel)
        spec = task(resolved_kernel, *resolved_args, task_id=task_id, kind=kind)
        self.tasks.append(spec)
        builder = WSPTaskBuilder(owner=self, spec=spec)
        builder._apply_schedule_defaults(self._current_schedule_defaults())
        return builder

    def mainloop(
        self,
        kernel: KernelSpec | str | None = None,
        *args: str | KernelValue,
        task_id: str | None = None,
    ) -> WSPTaskBuilder:
        return self.launch(kernel, *args, task_id=task_id, kind="wsp_mainloop").role("mainloop")

    def task(
        self,
        kernel: KernelSpec | str | None = None,
        *args: str | KernelValue,
        task_id: str | None = None,
        kind: str = "kernel_call",
    ) -> WSPTaskBuilder:
        return self.launch(kernel, *args, task_id=task_id, kind=kind)

    @contextmanager
    def defaults(
        self,
        *,
        tile: Mapping[str, Any] | None = None,
        bind: Mapping[str, Any] | None = None,
        pipeline: Mapping[str, Any] | None = None,
        resources: Mapping[str, Any] | None = None,
        specialize: Mapping[str, Any] | None = None,
    ):
        frame: dict[str, dict[str, Any]] = {}
        if tile is not None:
            frame["tile"] = _normalize_schedule_payload("tile", tile)
        if bind is not None:
            frame["bind"] = _normalize_schedule_payload("bind", bind)
        if pipeline is not None:
            frame["pipeline"] = _normalize_schedule_payload("pipeline", pipeline)
        if resources is not None:
            frame["resources"] = _normalize_schedule_payload("resources", resources)
        if specialize is not None:
            frame["specialize"] = _normalize_schedule_payload("specialize", specialize)

        self._schedule_defaults_stack.append(frame)
        merged = self._current_schedule_defaults()
        for key, value in merged.items():
            self.schedule_state[key] = dict(value)
        try:
            yield self
        finally:
            self._schedule_defaults_stack.pop()

    def tile(self, *, block: tuple[int, int, int] | list[int]) -> WSPBuilder:
        self.schedule_state["tile"] = tile(block=block)
        return self

    def bind(self, *, grid: str | None = None, lane: str | None = None) -> WSPBuilder:
        self.schedule_state["bind"] = bind(grid=grid, lane=lane)
        return self

    def pipeline(self, *, depth: int, buffering: str = "double") -> WSPBuilder:
        self.schedule_state["pipeline"] = pipeline(depth=depth, buffering=buffering)
        return self

    def resources(self, *, num_warps: int) -> WSPBuilder:
        self.schedule_state["resources"] = resources(num_warps=num_warps)
        return self

    def specialize(self, *, operator: str, **attrs: Any) -> WSPBuilder:
        self.schedule_state["specialize"] = specialize(operator=operator, **attrs)
        return self

    def to_program(self) -> dict[str, Any]:
        return WSPProgramSpec(
            entry=self.entry,
            target=self.target,
            kernel=self.kernel_spec.to_payload(),
            workload=workload(
                entry=self.entry,
                tasks=self.tasks,
                channels=self.channels,
                dependencies=self.dependencies,
            ),
            schedule=self.schedule_state,
        ).to_program()

    def _default_args_for(self, kernel: KernelSpec | str) -> tuple[KernelValue, ...]:
        kernel_name = kernel.name if isinstance(kernel, KernelSpec) else str(kernel)
        if kernel_name != self.kernel_spec.name:
            return ()
        return self.args.ordered()

    def _current_schedule_defaults(self) -> dict[str, dict[str, Any]]:
        merged = {key: {} for key in self.schedule_state}
        for frame in self._schedule_defaults_stack:
            for key, value in frame.items():
                merged[key] = dict(value)
        return merged


@dataclass
class WSPStageBuilder:
    task: WSPTaskBuilder
    stage_spec: dict[str, Any]

    def step(self, op: str, /, **attrs: Any) -> WSPStageBuilder:
        payload = {"kind": "step", "op": str(op)}
        payload.update({key: _stage_attr_value(value) for key, value in attrs.items()})
        self.stage_spec.setdefault("steps", []).append(payload)
        return self


@dataclass
class WSPTaskBuilder:
    """Fluent task handle for WSP programs.

    The task handle keeps HTP on a single shared program model while letting
    public WSP examples express producer/consumer roles, stage plans, and
    dependencies in a more meaningful way.
    """

    owner: WSPBuilder
    spec: dict[str, Any]

    @property
    def task_id(self) -> str:
        return str(self.spec["task_id"])

    def tile(self, *, block: tuple[int, int, int] | list[int]) -> WSPTaskBuilder:
        tile_payload = tile(block=block)
        self.owner.schedule_state["tile"] = tile_payload
        self._task_schedule()["tile"] = dict(tile_payload)
        return self

    def bind(self, *, grid: str | None = None, lane: str | None = None) -> WSPTaskBuilder:
        bind_payload = bind(grid=grid, lane=lane)
        self.owner.schedule_state["bind"] = bind_payload
        self._task_schedule()["bind"] = dict(bind_payload)
        return self

    def pipeline(self, *, depth: int, buffering: str = "double") -> WSPTaskBuilder:
        pipeline_payload = pipeline(depth=depth, buffering=buffering)
        self.owner.schedule_state["pipeline"] = pipeline_payload
        self._task_schedule()["pipeline"] = dict(pipeline_payload)
        return self

    def resources(self, *, num_warps: int) -> WSPTaskBuilder:
        resource_payload = resources(num_warps=num_warps)
        self.owner.schedule_state["resources"] = resource_payload
        self._task_schedule()["resources"] = dict(resource_payload)
        return self

    def specialize(self, *, operator: str, **attrs: Any) -> WSPTaskBuilder:
        specialize_payload = specialize(operator=operator, **attrs)
        self.owner.schedule_state["specialize"] = specialize_payload
        self._task_schedule()["specialize"] = dict(specialize_payload)
        return self

    def role(self, name: str) -> WSPTaskBuilder:
        self._attrs()["role"] = str(name)
        return self

    def after(self, other: str | WSPTaskBuilder) -> WSPTaskBuilder:
        src = other if isinstance(other, str) else other.task_id
        dependency = {"src": str(src), "dst": self.task_id}
        if dependency not in self.owner.dependencies:
            self.owner.dependencies.append(dependency)
        return self

    def stage(self, name: str, *steps: str) -> WSPTaskBuilder:
        if steps:
            self._stage_spec(name)["steps"].extend(str(step) for step in steps)
            return self
        return WSPStageBuilder(task=self, stage_spec=self._stage_spec(name))

    def prologue(self, *steps: str) -> WSPTaskBuilder | WSPStageBuilder:
        return self.stage("prologue", *steps)

    def steady(self, *steps: str) -> WSPTaskBuilder | WSPStageBuilder:
        return self.stage("steady", *steps)

    def epilogue(self, *steps: str) -> WSPTaskBuilder | WSPStageBuilder:
        return self.stage("epilogue", *steps)

    def _apply_schedule_defaults(self, defaults: Mapping[str, Mapping[str, Any]]) -> None:
        task_schedule = self._task_schedule()
        for key, value in defaults.items():
            if value:
                task_schedule.setdefault(key, dict(value))

    def _attrs(self) -> dict[str, Any]:
        attrs = self.spec.setdefault("attrs", {})
        if not isinstance(attrs, dict):
            attrs = {}
            self.spec["attrs"] = attrs
        return attrs

    def _task_schedule(self) -> dict[str, Any]:
        return self._attrs().setdefault("schedule", {})

    def _stage_spec(self, name: str) -> dict[str, Any]:
        stages = self._attrs().setdefault("stages", [])
        for stage in stages:
            if stage.get("name") == str(name):
                stage.setdefault("steps", [])
                return stage
        stage = {"name": str(name), "steps": []}
        stages.append(stage)
        return stage


def program(
    *,
    entry: str | None = None,
    kernel: Mapping[str, Any] | KernelSpec,
    workload: Mapping[str, Any] | None = None,
    tasks: Sequence[Mapping[str, Any]] | None = None,
    schedule: Mapping[str, Any] | None = None,
    target: Mapping[str, Any] | str | None = None,
) -> dict[str, Any] | Callable[[Callable[..., Any]], WSPProgramSpec]:
    kernel_payload = kernel.to_payload() if isinstance(kernel, KernelSpec) else dict(kernel)

    if (
        workload is not None
        or tasks is not None
        or schedule is not None
        or entry is not None
        and isinstance(kernel, Mapping)
    ):
        if entry is None:
            raise TypeError(
                "wsp.program(..., kernel=<mapping>, ...) requires entry= when used as a payload builder."
            )
        workload_payload = (
            dict(workload)
            if workload is not None
            else {
                "entry": entry,
                "tasks": [dict(item) for item in (tasks or ())],
                "channels": [],
                "dependencies": [],
            }
        )
        return {
            "entry": entry,
            "target": _normalize_target(target),
            "kernel": kernel_payload,
            "wsp": {
                "workload": workload_payload,
                "schedule": dict(schedule or {}),
            },
        }

    if not isinstance(kernel, KernelSpec):
        raise TypeError("Decorator-form wsp.program(...) requires kernel=<KernelSpec>.")

    def decorator(function: Callable[..., Any]) -> WSPProgramSpec:
        builder = WSPBuilder(
            entry=entry or function.__name__,
            kernel_spec=kernel,
            target=_normalize_target(target),
        )
        if len(signature(function).parameters) == 0:
            function()
        else:
            function(builder)
        return WSPProgramSpec(
            entry=builder.entry,
            target=builder.target,
            kernel=builder.kernel_spec.to_payload(),
            workload={
                "entry": builder.entry,
                "tasks": [dict(item) for item in builder.tasks],
                "channels": [dict(item) for item in builder.channels],
                "dependencies": [dict(item) for item in builder.dependencies],
            },
            schedule=builder.schedule_state,
        )

    return decorator


def _normalize_target(target: Mapping[str, Any] | str | None) -> dict[str, Any]:
    if target is None:
        return {}
    if isinstance(target, str):
        target_spec = parse_target(target)
        payload = {"backend": target_spec.backend}
        if target_spec.option is not None:
            payload["option"] = target_spec.option
        return payload
    return dict(target)


def _normalize_schedule_payload(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if kind == "tile":
        return tile(block=tuple(payload["block"]))
    if kind == "bind":
        return bind(grid=payload.get("grid"), lane=payload.get("lane"))
    if kind == "pipeline":
        return pipeline(depth=int(payload["depth"]), buffering=str(payload.get("buffering", "double")))
    if kind == "resources":
        return resources(num_warps=int(payload["num_warps"]))
    if kind == "specialize":
        operator = payload.get("operator")
        if operator is None:
            return {}
        return specialize(operator=str(operator), **{k: v for k, v in payload.items() if k != "operator"})
    raise ValueError(f"Unsupported WSP schedule payload kind {kind!r}.")


def _ref(value: str | KernelValue) -> str:
    if isinstance(value, KernelValue):
        return value.name
    return str(value)


def _stage_attr_value(value: Any) -> Any:
    if isinstance(value, KernelValue):
        return value.name
    return value


__all__ = [
    "WSPBuilder",
    "WSPTaskBuilder",
    "WSPProgramSpec",
    "build_wsp_program_module",
    "bind",
    "pipeline",
    "program",
    "resources",
    "schedule",
    "specialize",
    "task",
    "tile",
    "workload",
]
