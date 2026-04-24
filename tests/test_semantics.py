import unittest

from intellic.ir.dialects import affine, arith, memref
from intellic.ir.semantics import (
    RelationSchema,
    SemanticDef,
    SemanticLevelKey,
    SemanticRegistry,
    TraceDB,
    execute_function,
    record_affine_memory_effect,
)
from intellic.ir.syntax import Operation, Type, i32, index
from intellic.surfaces.api import arith as surface_arith
from intellic.surfaces.api import func as surface_func
from intellic.surfaces.api import scf as surface_scf


class SemanticsTests(unittest.TestCase):
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
