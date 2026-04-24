from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
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


class GuardedList(list):
    def __init__(self, owner: object, field: str, values: Iterable[object] = ()) -> None:
        super().__init__(values)
        self._owner = owner
        self._field = field

    def _record(self, kind: str) -> None:
        record_direct_mutation_attempt(f"{self._prefix}_{kind}", self._owner, field=self._field)

    @property
    def _prefix(self) -> str:
        if self._field == "_blocks":
            return "region_blocks"
        return "block_operations"

    def __setitem__(self, index, value) -> None:
        self._record("update")
        super().__setitem__(index, value)

    def __delitem__(self, index) -> None:
        self._record("delete")
        super().__delitem__(index)

    def append(self, value: object) -> None:
        self._record("append")
        super().append(value)

    def clear(self) -> None:
        self._record("clear")
        super().clear()

    def extend(self, values: Iterable[object]) -> None:
        self._record("extend")
        super().extend(values)

    def insert(self, index: int, value: object) -> None:
        self._record("insert")
        super().insert(index, value)

    def pop(self, index: int = -1) -> object:
        self._record("delete")
        return super().pop(index)

    def remove(self, value: object) -> None:
        self._record("delete")
        super().remove(value)

    def reverse(self) -> None:
        self._record("reorder")
        super().reverse()

    def sort(self, *args: object, **kwargs: Any) -> None:
        self._record("reorder")
        super().sort(*args, **kwargs)

    def __iadd__(self, values: Iterable[object]):
        self._record("extend")
        return super().__iadd__(values)
