import unittest

from intellic.dialects import affine, arith, builtin, func, memref
from intellic.ir.semantics import (
    Interpreter,
    RelationSchema,
    SemanticDef,
    SemanticLevelKey,
    SemanticRegistry,
    TraceDB,
    execute_function,
    record_affine_memory_effect,
)
from intellic.ir.syntax import Block, Builder, Operation, Region, Type, i32, index
from intellic.surfaces.api import arith as surface_arith
from intellic.surfaces.api import func as surface_func
from intellic.surfaces.api import scf as surface_scf


class SemanticsTests(unittest.TestCase):
    def _function_with_body(self, name, inputs, results, build_body):
        entry = Block(arg_types=inputs)
        body = Region.from_block_list([entry])
        builder = Builder()
        with builder.insert_at_end(entry):
            build_body(builder, entry.arguments)
        return func.func(name, func.FunctionType(inputs=inputs, results=results), body)

    def _module_with_functions(self, *functions):
        body = Region.from_block_list([Block()])
        module = builtin.module(body)
        builder = Builder()
        with builder.insert_at_end(body.blocks[0]):
            for function in functions:
                builder.insert(function)
        return module

    def test_trace_db_current_history_and_require(self) -> None:
        db = TraceDB()
        schema = RelationSchema("ValueConcrete")
        record = db.put(schema, subject="v0", value=1)

        self.assertEqual(db.require("ValueConcrete", "v0").value, 1)

        db.retract(record.id, reason="superseded")

        with self.assertRaisesRegex(KeyError, "missing required fact"):
            db.require("ValueConcrete", "v0")
        self.assertEqual(len(db.history("ValueConcrete", "v0")), 1)

    def test_registry_rejects_duplicate_without_policy(self) -> None:
        registry = SemanticRegistry()
        level = SemanticLevelKey("ConcreteValue")
        first = SemanticDef(owner="arith.addi", level=level, apply=lambda *_: None)
        duplicate = SemanticDef(owner="arith.addi", level=level, apply=lambda *_: None)

        registry.register(first)

        with self.assertRaisesRegex(ValueError, "duplicate"):
            registry.register(duplicate)

    def test_execute_sum_to_n_records_loop_iterations(self) -> None:
        @surface_func.ir_function
        def sum_to_n(n: index) -> i32:
            zero_i = surface_arith.constant(0, index)
            one_i = surface_arith.constant(1, index)
            zero = surface_arith.constant(0, i32)

            with surface_scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
                i, total = loop.arguments
                total_next = surface_arith.addi(total, surface_arith.index_cast(i, i32))
                surface_scf.yield_(total_next)

            return loop.results[0]

        db = TraceDB()
        result = execute_function(sum_to_n.operation, (5,), db)

        self.assertEqual(result, (10,))
        self.assertEqual(len(db.query("LoopIteration")), 5)
        self.assertEqual(db.require("RegionResult", sum_to_n.operation.id).value, (10,))

    def test_func_call_executes_module_local_callee_and_records_trace(self) -> None:
        def build_increment(builder, arguments):
            one = builder.insert(arith.constant(1, i32)).results[0]
            total = builder.insert(arith.addi(arguments[0], one)).results[0]
            builder.insert(func.return_(total))

        callee_type = func.FunctionType(inputs=(i32,), results=(i32,))
        increment = self._function_with_body("increment", (i32,), (i32,), build_increment)

        call_holder = {}

        def build_caller(builder, arguments):
            call = builder.insert(func.call("increment", (arguments[0],), callee_type))
            call_holder["op"] = call
            builder.insert(func.return_(call.results[0]))

        caller = self._function_with_body("caller", (i32,), (i32,), build_caller)
        self._module_with_functions(increment, caller)
        db = TraceDB()

        result = Interpreter(db).execute_function(caller, (41,))

        self.assertEqual(result, (42,))
        call = call_holder["op"]
        self.assertEqual(db.require("Call", call.id).value["callee"], "increment")
        self.assertEqual(db.require("Evaluated", call.id).value, (42,))

    def test_func_call_rejects_unknown_callee(self) -> None:
        callee_type = func.FunctionType(inputs=(i32,), results=(i32,))

        def build_caller(builder, arguments):
            call = builder.insert(func.call("missing", (arguments[0],), callee_type))
            builder.insert(func.return_(call.results[0]))

        caller = self._function_with_body("caller", (i32,), (i32,), build_caller)
        self._module_with_functions(caller)

        with self.assertRaisesRegex(KeyError, "unknown func.call callee"):
            Interpreter().execute_function(caller, (7,))

    def test_func_call_rejects_mismatched_callee_return_count(self) -> None:
        def build_bad_callee(builder, arguments):
            builder.insert(func.return_(arguments[0], arguments[0]))

        bad = self._function_with_body("bad", (i32,), (i32,), build_bad_callee)
        callee_type = func.FunctionType(inputs=(i32,), results=(i32,))

        def build_caller(builder, arguments):
            call = builder.insert(func.call("bad", (arguments[0],), callee_type))
            builder.insert(func.return_(call.results[0]))

        caller = self._function_with_body("caller", (i32,), (i32,), build_caller)
        self._module_with_functions(bad, caller)

        with self.assertRaisesRegex(ValueError, "func.call returned wrong result count"):
            Interpreter().execute_function(caller, (7,))

    def test_func_call_rejects_mismatched_callee_return_type(self) -> None:
        def build_bad_callee(builder, arguments):
            builder.insert(func.return_(arguments[0]))

        bad = self._function_with_body("bad", (index,), (i32,), build_bad_callee)
        callee_type = func.FunctionType(inputs=(index,), results=(i32,))

        def build_caller(builder, arguments):
            call = builder.insert(func.call("bad", (arguments[0],), callee_type))
            builder.insert(func.return_(call.results[0]))

        caller = self._function_with_body("caller", (index,), (i32,), build_caller)
        self._module_with_functions(bad, caller)

        with self.assertRaisesRegex(TypeError, "func.return operand 0 type mismatch"):
            Interpreter().execute_function(caller, (7,))

    def test_affine_memory_effect_records_access_fact(self) -> None:
        f32 = Type("f32")
        mem_type = memref.MemRefType(f32, (None,))
        mem = Operation.create("test.arg", result_types=(mem_type,)).results[0]
        idx = arith.constant(0, index).results[0]
        map_ = affine.AffineMap(1, 0, ("d0",))
        load = affine.load(mem, map_, dims=(idx,), symbols=())
        db = TraceDB()

        record_affine_memory_effect(load, db)

        access = db.require("AffineAccess", load.id).value
        effect = db.require("MemoryEffect", load.id).value
        self.assertEqual(access["kind"], "read")
        self.assertEqual(access["rank"], 1)
        self.assertEqual(effect["kind"], "read")


if __name__ == "__main__":
    unittest.main()
