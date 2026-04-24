from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any


_ACTIVE_MUTATION_ATTEMPTS: ContextVar[list[dict[str, object]] | None] = ContextVar(
    "active_syntax_mutation_attempts",
    default=None,
)
_MISSING = object()


@contextmanager
def direct_mutation_guard() -> Iterator[list[dict[str, object]]]:
    attempts: list[dict[str, object]] = []
    token = _ACTIVE_MUTATION_ATTEMPTS.set(attempts)
    try:
        yield attempts
    finally:
        _ACTIVE_MUTATION_ATTEMPTS.reset(token)


def record_direct_mutation_attempt(kind: str, subject: object, **details: object) -> None:
    attempts = _ACTIVE_MUTATION_ATTEMPTS.get()
    if attempts is None:
        return
    attempts.append({"kind": kind, "subject": subject, **details})


class GuardedDict(dict):
    def __init__(self, owner: object, field: str, values: Mapping[str, Any]) -> None:
        super().__init__(values)
        self._owner = owner
        self._field = field

    def __setitem__(self, key: str, value: Any) -> None:
        record_direct_mutation_attempt(
            "metadata_update",
            self._owner,
            field=self._field,
            key=key,
        )
        super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        record_direct_mutation_attempt(
            "metadata_delete",
            self._owner,
            field=self._field,
            key=key,
        )
        super().__delitem__(key)

    def clear(self) -> None:
        record_direct_mutation_attempt("metadata_clear", self._owner, field=self._field)
        super().clear()

    def pop(self, key: str, default: Any = _MISSING) -> Any:
        record_direct_mutation_attempt(
            "metadata_delete",
            self._owner,
            field=self._field,
            key=key,
        )
        if default is _MISSING:
            return super().pop(key)
        return super().pop(key, default)

    def popitem(self) -> tuple[str, Any]:
        record_direct_mutation_attempt("metadata_delete", self._owner, field=self._field)
        return super().popitem()

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key not in self:
            record_direct_mutation_attempt(
                "metadata_update",
                self._owner,
                field=self._field,
                key=key,
            )
        return super().setdefault(key, default)

    def update(self, *args: object, **kwargs: Any) -> None:
        if args or kwargs:
            record_direct_mutation_attempt("metadata_update", self._owner, field=self._field)
        super().update(*args, **kwargs)

    def __ior__(self, other: object):
        record_direct_mutation_attempt("metadata_update", self._owner, field=self._field)
        return super().__ior__(other)
