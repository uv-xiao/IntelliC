from __future__ import annotations

from dataclasses import dataclass

from intellic.ir.syntax import Operation, Value

from .trace_db import TraceDB


@dataclass(frozen=True)
class _ReturnSignal(Exception):
    values: tuple[object, ...]


@dataclass(frozen=True)
class _YieldSignal(Exception):
    values: tuple[object, ...]


class Interpreter:
    def __init__(self, db: TraceDB | None = None) -> None:
        self.db = db or TraceDB()
        self.values: dict[Value, object] = {}

    def execute_function(self, func_op: Operation, inputs: tuple[object, ...]) -> tuple[object, ...]:
        entry = func_op.regions[0].blocks[0]
        if len(entry.arguments) != len(inputs):
            raise ValueError("function input count mismatch")
        for arg, value in zip(entry.arguments, inputs):
            self.values[arg] = value
            self.db.put("ValueConcrete", arg.id, value)
        try:
            self._execute_block(entry)
        except _ReturnSignal as signal:
            self.db.put("RegionResult", func_op.id, signal.values)
            return signal.values
        raise ValueError("function did not return")

    def _execute_block(self, block) -> None:
        for op in block.operations:
            self._execute_op(op)

    def _execute_op(self, op: Operation) -> None:
        if op.name == "arith.constant":
            value = op.properties["value"]
            self._write_results(op, (value,))
            return
        if op.name == "arith.index_cast":
            self._write_results(op, (int(self._read(op.operands[0])),))
            return
        if op.name == "arith.addi":
            self._write_results(op, (self._read(op.operands[0]) + self._read(op.operands[1]),))
            return
        if op.name == "scf.for":
            self._execute_for(op)
            return
        if op.name == "scf.yield":
            raise _YieldSignal(tuple(self._read(operand) for operand in op.operands))
        if op.name == "func.return":
            raise _ReturnSignal(tuple(self._read(operand) for operand in op.operands))

    def _execute_for(self, op: Operation) -> None:
        lower = int(self._read(op.operands[0]))
        upper = int(self._read(op.operands[1]))
        step = int(self._read(op.operands[2]))
        carried = tuple(self._read(operand) for operand in op.operands[3:])
        body = op.regions[0].blocks[0]
        for iteration, iv in enumerate(range(lower, upper, step)):
            self.values[body.arguments[0]] = iv
            for arg, value in zip(body.arguments[1:], carried):
                self.values[arg] = value
            try:
                self._execute_block(body)
            except _YieldSignal as signal:
                carried = signal.values
                self.db.put("LoopIteration", op.id, {"iteration": iteration, "iv": iv, "yielded": carried})
                continue
            raise ValueError("scf.for body did not yield")
        self._write_results(op, carried)

    def _read(self, value: Value) -> object:
        try:
            return self.values[value]
        except KeyError as exc:
            raise KeyError(f"missing concrete value for {value.id}") from exc

    def _write_results(self, op: Operation, values: tuple[object, ...]) -> None:
        if len(values) != len(op.results):
            raise ValueError(f"{op.name} produced wrong result count")
        for result, value in zip(op.results, values):
            self.values[result] = value
            self.db.put("ValueConcrete", result.id, value)
        self.db.put("Evaluated", op.id, values)


def execute_function(func_op: Operation, inputs: tuple[object, ...], db: TraceDB | None = None) -> tuple[object, ...]:
    return Interpreter(db).execute_function(func_op, inputs)
