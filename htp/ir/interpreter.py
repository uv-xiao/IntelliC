from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from htp.runtime.core import Runtime


class ProgramModuleInterpreter(Protocol):
    def run(
        self,
        module: Any,
        *,
        entry: str,
        args: tuple[Any, ...],
        kwargs: Mapping[str, Any],
        mode: str,
        runtime: Runtime | None,
        trace: Any | None,
    ) -> Any: ...


@dataclass(frozen=True)
class InterpreterSpec:
    interpreter_id: str
    runner: Callable[..., Any]

    def run(
        self,
        module: Any,
        *,
        entry: str,
        args: tuple[Any, ...],
        kwargs: Mapping[str, Any],
        mode: str,
        runtime: Runtime | None,
        trace: Any | None,
    ) -> Any:
        return self.runner(
            module,
            entry=entry,
            args=args,
            kwargs=kwargs,
            mode=mode,
            runtime=runtime,
            trace=trace,
        )


def _snapshot_runner(
    module: Any,
    *,
    entry: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
    mode: str,
    runtime: Runtime | None,
    trace: Any | None,
) -> Any:
    del entry, args, kwargs, mode, runtime, trace
    return module.to_program_dict()


SNAPSHOT_INTERPRETER_ID = "htp.interpreter.snapshot.v1"

_REGISTRY: dict[str, InterpreterSpec] = {
    SNAPSHOT_INTERPRETER_ID: InterpreterSpec(
        interpreter_id=SNAPSHOT_INTERPRETER_ID,
        runner=_snapshot_runner,
    )
}


def register_interpreter(interpreter_id: str, runner: Callable[..., Any]) -> None:
    _REGISTRY[str(interpreter_id)] = InterpreterSpec(interpreter_id=str(interpreter_id), runner=runner)


def get_interpreter(interpreter_id: str) -> InterpreterSpec:
    try:
        return _REGISTRY[str(interpreter_id)]
    except KeyError as exc:
        raise KeyError(f"Unknown ProgramModule interpreter: {interpreter_id}") from exc


def run_program_module(
    module: Any,
    *,
    interpreter_id: str,
    entry: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
    mode: str,
    runtime: Runtime | None,
    trace: Any | None,
) -> Any:
    return get_interpreter(interpreter_id).run(
        module,
        entry=entry,
        args=args,
        kwargs=kwargs,
        mode=mode,
        runtime=runtime,
        trace=trace,
    )


__all__ = [
    "ProgramModuleInterpreter",
    "SNAPSHOT_INTERPRETER_ID",
    "get_interpreter",
    "register_interpreter",
    "run_program_module",
]
