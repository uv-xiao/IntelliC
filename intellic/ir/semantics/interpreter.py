from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from intellic.ir.dialects.func import FunctionType
from intellic.ir.syntax import Operation, Value

from .trace_db import TraceDB


@dataclass
class _ReturnSignal(Exception):
    values: tuple[object, ...]


@dataclass
class _YieldSignal(Exception):
    values: tuple[object, ...]


class Interpreter:
    """Concrete interpreter with optional function symbols for direct calls."""

    def __init__(
        self,
        db: TraceDB | None = None,
        symbols: Mapping[str, Operation] | None = None,
        module: Operation | None = None,
    ) -> None:
        self.db = db or TraceDB()
        self.symbols: dict[str, Operation] = dict(symbols or {})
        if module is not None:
            self._add_module_symbols(module)
        self.values: dict[Value, object] = {}
        self._call_stack: list[str] = []

    def execute_function(self, func_op: Operation, inputs: tuple[object, ...]) -> tuple[object, ...]:
        self._ensure_symbol_table(func_op)
        returned = self._invoke_function(func_op, inputs)
        self._validate_function_results(func_op, returned)
        self.db.put("RegionResult", func_op.id, returned)
        return returned

    def _invoke_function(self, func_op: Operation, inputs: tuple[object, ...]) -> tuple[object, ...]:
        function_name = func_op.properties.get("sym_name")
        if isinstance(function_name, str):
            self._call_stack.append(function_name)
        entry = func_op.regions[0].blocks[0]
        function_type = self._function_type(func_op)
        try:
            if len(entry.arguments) != len(inputs):
                raise ValueError("function input count mismatch")
            if len(function_type.inputs) != len(inputs):
                raise ValueError("function input count mismatch")
            for arg, value in zip(entry.arguments, inputs):
                self.values[arg] = value
                self.db.put("ValueConcrete", arg.id, value)
            try:
                self._execute_block(entry)
            except _ReturnSignal as signal:
                return signal.values
            raise ValueError("function did not return")
        finally:
            if isinstance(function_name, str):
                self._call_stack.pop()

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
        if op.name == "func.call":
            self._execute_call(op)
            return
        if op.name == "scf.yield":
            raise _YieldSignal(tuple(self._read(operand) for operand in op.operands))
        if op.name == "func.return":
            self._execute_return(op)
            return

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

    def _execute_call(self, op: Operation) -> None:
        callee_name = op.properties["callee"]
        callee = self.symbols.get(callee_name)
        if callee is None:
            raise KeyError(f"unknown func.call callee: {callee_name}")
        if callee_name in self._call_stack:
            raise ValueError(f"recursive func.call is unsupported: {callee_name}")

        call_type = self._call_type(op)
        callee_type = self._function_type(callee)
        self._validate_call_signature(op, call_type, callee_type)
        arguments = tuple(self._read(operand) for operand in op.operands)

        returned = self._invoke_function(callee, arguments)

        if len(returned) != len(op.results):
            raise ValueError("func.call returned wrong result count")
        for index, (result, expected_type) in enumerate(zip(op.results, call_type.results)):
            if result.type != expected_type:
                raise TypeError(f"func.call result {index} type mismatch")
        self._write_results(op, returned)
        self.db.put(
            "Call",
            op.id,
            {
                "callee": callee_name,
                "callee_id": callee.id,
                "args": arguments,
                "results": returned,
            },
        )

    def _execute_return(self, op: Operation) -> None:
        func_op = self._enclosing_function(op)
        if func_op is None:
            raise ValueError("func.return outside func.func")
        function_type = self._function_type(func_op)
        for index, (operand, expected_type) in enumerate(zip(op.operands, function_type.results)):
            if operand.type != expected_type:
                raise TypeError(f"func.return operand {index} type mismatch")
        raise _ReturnSignal(tuple(self._read(operand) for operand in op.operands))

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

    def _ensure_symbol_table(self, func_op: Operation) -> None:
        module = self._enclosing_module(func_op)
        if module is not None:
            self._add_module_symbols(module)
        name = func_op.properties.get("sym_name")
        if isinstance(name, str):
            self.symbols.setdefault(name, func_op)

    def _add_module_symbols(self, module: Operation) -> None:
        if module.name != "builtin.module":
            raise ValueError("symbol table module must be a builtin.module")
        for region in module.regions:
            for block in region.blocks:
                for op in block.operations:
                    if op.name != "func.func":
                        continue
                    name = op.properties["sym_name"]
                    existing = self.symbols.get(name)
                    if existing is not None and existing is not op:
                        raise ValueError(f"duplicate function symbol: {name}")
                    self.symbols[name] = op

    def _enclosing_module(self, op: Operation) -> Operation | None:
        parent = op.parent
        while parent is not None:
            if isinstance(parent, Operation):
                if parent.name == "builtin.module":
                    return parent
                parent = parent.parent
                continue
            parent = getattr(parent, "parent", None)
        return None

    def _enclosing_function(self, op: Operation) -> Operation | None:
        parent = op.parent
        while parent is not None:
            if isinstance(parent, Operation):
                if parent.name == "func.func":
                    return parent
                parent = parent.parent
                continue
            parent = getattr(parent, "parent", None)
        return None

    def _function_type(self, op: Operation) -> FunctionType:
        function_type = op.properties.get("function_type")
        if not isinstance(function_type, FunctionType):
            raise TypeError(f"{op.name} missing function type")
        return function_type

    def _call_type(self, op: Operation) -> FunctionType:
        call_type = op.properties.get("function_type")
        if not isinstance(call_type, FunctionType):
            raise TypeError("func.call missing function type")
        return call_type

    def _validate_call_signature(
        self,
        op: Operation,
        call_type: FunctionType,
        callee_type: FunctionType,
    ) -> None:
        if call_type.inputs != callee_type.inputs:
            raise TypeError("func.call argument type mismatch")
        if call_type.results != callee_type.results:
            raise TypeError("func.call result type mismatch")
        if len(op.operands) != len(callee_type.inputs):
            raise ValueError("func.call argument count mismatch")
        if len(op.results) != len(callee_type.results):
            raise ValueError("func.call result count mismatch")
        for index, (operand, expected_type) in enumerate(zip(op.operands, callee_type.inputs)):
            if operand.type != expected_type:
                raise TypeError(f"func.call argument {index} type mismatch")
        for index, (result, expected_type) in enumerate(zip(op.results, callee_type.results)):
            if result.type != expected_type:
                raise TypeError(f"func.call result {index} type mismatch")

    def _validate_function_results(self, func_op: Operation, values: tuple[object, ...]) -> None:
        function_type = self._function_type(func_op)
        if len(values) != len(function_type.results):
            raise ValueError(f"{func_op.name} returned wrong result count")


def execute_function(func_op: Operation, inputs: tuple[object, ...], db: TraceDB | None = None) -> tuple[object, ...]:
    return Interpreter(db).execute_function(func_op, inputs)
