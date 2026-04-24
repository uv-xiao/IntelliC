from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, MutableMapping, MutableSequence
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


class GuardedDict(MutableMapping):
    def __init__(self, owner: object, field: str, values: Mapping[str, Any]) -> None:
        self._data = dict(values)
        self._owner = owner
        self._field = field

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __setitem__(self, key: str, value: Any) -> None:
        record_direct_mutation_attempt(
            "metadata_update",
            self._owner,
            field=self._field,
            key=key,
        )
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        record_direct_mutation_attempt(
            "metadata_delete",
            self._owner,
            field=self._field,
            key=key,
        )
        del self._data[key]

    def clear(self) -> None:
        record_direct_mutation_attempt("metadata_clear", self._owner, field=self._field)
        self._data.clear()

    def pop(self, key: str, default: Any = _MISSING) -> Any:
        record_direct_mutation_attempt(
            "metadata_delete",
            self._owner,
            field=self._field,
            key=key,
        )
        if default is _MISSING:
            return self._data.pop(key)
        return self._data.pop(key, default)

    def popitem(self) -> tuple[str, Any]:
        record_direct_mutation_attempt("metadata_delete", self._owner, field=self._field)
        return self._data.popitem()

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key not in self:
            record_direct_mutation_attempt(
                "metadata_update",
                self._owner,
                field=self._field,
                key=key,
            )
        return self._data.setdefault(key, default)

    def update(self, *args: object, **kwargs: Any) -> None:
        if args or kwargs:
            record_direct_mutation_attempt("metadata_update", self._owner, field=self._field)
        self._data.update(*args, **kwargs)

    def __ior__(self, other: object):
        record_direct_mutation_attempt("metadata_update", self._owner, field=self._field)
        self._data |= dict(other)
        return self

    def __repr__(self) -> str:
        return repr(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return self._data == dict(other)
        return False


class GuardedList(MutableSequence):
    def __init__(self, owner: object, field: str, values: Iterable[object] = ()) -> None:
        self._data = list(values)
        self._owner = owner
        self._field = field

    def _record(self, kind: str) -> None:
        record_direct_mutation_attempt(f"{self._prefix}_{kind}", self._owner, field=self._field)

    @property
    def _prefix(self) -> str:
        if self._field == "_blocks":
            return "region_blocks"
        return "block_operations"

    def __getitem__(self, index):
        return self._data[index]

    def __len__(self) -> int:
        return len(self._data)

    def __setitem__(self, index, value) -> None:
        self._record("update")
        self._data[index] = value

    def __delitem__(self, index) -> None:
        self._record("delete")
        del self._data[index]

    def clear(self) -> None:
        self._record("clear")
        self._data.clear()

    def extend(self, values: Iterable[object]) -> None:
        self._record("extend")
        self._data.extend(values)

    def insert(self, index: int, value: object) -> None:
        self._record("insert")
        self._data.insert(index, value)

    def pop(self, index: int = -1) -> object:
        self._record("delete")
        return self._data.pop(index)

    def remove(self, value: object) -> None:
        self._record("delete")
        self._data.remove(value)

    def reverse(self) -> None:
        self._record("reorder")
        self._data.reverse()

    def sort(self, *args: object, **kwargs: Any) -> None:
        self._record("reorder")
        self._data.sort(*args, **kwargs)

    def __iadd__(self, values: Iterable[object]):
        self._record("extend")
        self._data += list(values)
        return self

    def __repr__(self) -> str:
        return repr(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Iterable):
            return self._data == list(other)
        return False
