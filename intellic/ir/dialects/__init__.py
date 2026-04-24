"""Compatibility namespace for concrete dialects.

Concrete dialect definitions live in :mod:`intellic.dialects`.
"""

from intellic.dialects import affine, arith, builtin, func, memref, scf, vector

__all__ = ("affine", "arith", "builtin", "func", "memref", "scf", "vector")
