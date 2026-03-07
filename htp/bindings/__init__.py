"""Bindings package."""

import sys

from .api import bind
from .base import BindingSession, BuildResult, ManifestBinding, ReplayResult, RunResult, ValidationResult

parent = sys.modules.get("htp")
if parent is not None and not hasattr(parent, "bind"):
    parent.bind = bind

__all__ = [
    "BindingSession",
    "BuildResult",
    "ManifestBinding",
    "ReplayResult",
    "RunResult",
    "ValidationResult",
    "bind",
]
