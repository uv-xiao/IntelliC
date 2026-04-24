from __future__ import annotations

from intellic.ir.dialects.affine import AffineMap
from intellic.ir.dialects.memref import MemRefType
from intellic.ir.syntax import Operation

from .trace_db import TraceDB


def record_affine_memory_effect(op: Operation, db: TraceDB) -> None:
    if op.name not in {"affine.load", "affine.store", "affine.vector_load", "affine.vector_store"}:
        raise ValueError("expected affine memory operation")
    if op.name in {"affine.load", "affine.vector_load"}:
        memref_value = op.operands[0]
        kind = "read"
    else:
        memref_value = op.operands[1]
        kind = "write"
    memref_type = memref_value.type
    if not isinstance(memref_type, MemRefType):
        raise TypeError("affine memory fact requires memref operand")
    map_ = op.properties["map"]
    if not isinstance(map_, AffineMap):
        raise TypeError("affine memory fact requires affine map property")
    access = {
        "memref": memref_value.id,
        "element_type": memref_type.element_type,
        "rank": memref_type.rank,
        "map": map_,
        "kind": kind,
    }
    db.put("AffineAccess", op.id, access)
    db.put("MemoryEffect", op.id, {"kind": kind, "subject": memref_value.id})
