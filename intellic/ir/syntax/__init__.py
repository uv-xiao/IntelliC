"""Syntax objects for IntelliC IR."""

from .attribute import Attribute
from .builder import Builder, InsertionPoint
from .context import Context
from .ids import SyntaxId
from .location import GENERATED, SourceLocation
from .operation import Operation
from .region import Block, Region
from .type import Type, i1, i32, index
from .value import BlockArgument, OpResult, Use, Value
from .verify import VerificationError, verify_operation

__all__ = (
    "Attribute",
    "Block",
    "BlockArgument",
    "Builder",
    "Context",
    "GENERATED",
    "InsertionPoint",
    "OpResult",
    "Operation",
    "Region",
    "SourceLocation",
    "SyntaxId",
    "Type",
    "Use",
    "Value",
    "VerificationError",
    "i1",
    "i32",
    "index",
    "verify_operation",
)
