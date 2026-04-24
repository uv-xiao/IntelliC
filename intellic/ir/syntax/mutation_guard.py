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
        super().__setattr__("_data", tuple(dict(values).items()))
        super().__setattr__("_owner", owner)
        super().__setattr__("_field", field)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_data" and hasattr(self, "_data"):
            record_direct_mutation_attempt(
                "metadata_backing_assignment",
                self._owner,
                field=self._field,
            )
            value = tuple(dict(value).items()) if isinstance(value, Mapping) else tuple(value)
        super().__setattr__(name, value)

    def __getitem__(self, key: str) -> Any:
        for existing_key, value in self._data:
            if existing_key == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _value in self._data)

    def __len__(self) -> int:
        return len(self._data)

    def _with_item(self, key: str, value: Any) -> tuple[tuple[str, Any], ...]:
        items = list(self._data)
        for index, (existing_key, _existing_value) in enumerate(items):
            if existing_key == key:
                items[index] = (key, value)
                return tuple(items)
        items.append((key, value))
        return tuple(items)

    def _without_item(self, key: str) -> tuple[tuple[str, Any], ...]:
        items = list(self._data)
        for index, (existing_key, _existing_value) in enumerate(items):
            if existing_key == key:
                del items[index]
                return tuple(items)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        record_direct_mutation_attempt(
            "metadata_update",
            self._owner,
            field=self._field,
            key=key,
        )
        super().__setattr__("_data", self._with_item(key, value))

    def __delitem__(self, key: str) -> None:
        record_direct_mutation_attempt(
            "metadata_delete",
            self._owner,
            field=self._field,
            key=key,
        )
        super().__setattr__("_data", self._without_item(key))

    def clear(self) -> None:
        record_direct_mutation_attempt("metadata_clear", self._owner, field=self._field)
        super().__setattr__("_data", ())

    def pop(self, key: str, default: Any = _MISSING) -> Any:
        record_direct_mutation_attempt(
            "metadata_delete",
            self._owner,
            field=self._field,
            key=key,
        )
        try:
            value = self[key]
        except KeyError:
            if default is _MISSING:
                raise
            return default
        super().__setattr__("_data", self._without_item(key))
        return value

    def popitem(self) -> tuple[str, Any]:
        record_direct_mutation_attempt("metadata_delete", self._owner, field=self._field)
        if not self._data:
            raise KeyError("dictionary is empty")
        item = self._data[-1]
        super().__setattr__("_data", self._data[:-1])
        return item

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key not in self:
            record_direct_mutation_attempt(
                "metadata_update",
                self._owner,
                field=self._field,
                key=key,
            )
            super().__setattr__("_data", self._with_item(key, default))
            return default
        return self[key]

    def update(self, *args: object, **kwargs: Any) -> None:
        if args or kwargs:
            record_direct_mutation_attempt("metadata_update", self._owner, field=self._field)
        updates = dict(*args, **kwargs)
        for key, value in updates.items():
            super().__setattr__("_data", self._with_item(key, value))

    def __ior__(self, other: object):
        record_direct_mutation_attempt("metadata_update", self._owner, field=self._field)
        self.update(other)
        return self

    def __repr__(self) -> str:
        return repr(dict(self._data))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self._data) == dict(other)
        return False


class GuardedList(MutableSequence):
    def __init__(self, owner: object, field: str, values: Iterable[object] = ()) -> None:
        super().__setattr__("_data", tuple(values))
        super().__setattr__("_owner", owner)
        super().__setattr__("_field", field)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_data" and hasattr(self, "_data"):
            self._record("backing_assignment")
            value = tuple(value)
        super().__setattr__(name, value)

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
        items = list(self._data)
        items[index] = value
        super().__setattr__("_data", tuple(items))

    def __delitem__(self, index) -> None:
        self._record("delete")
        items = list(self._data)
        del items[index]
        super().__setattr__("_data", tuple(items))

    def clear(self) -> None:
        self._record("clear")
        super().__setattr__("_data", ())

    def extend(self, values: Iterable[object]) -> None:
        self._record("extend")
        super().__setattr__("_data", (*self._data, *tuple(values)))

    def insert(self, index: int, value: object) -> None:
        self._record("insert")
        items = list(self._data)
        items.insert(index, value)
        super().__setattr__("_data", tuple(items))

    def pop(self, index: int = -1) -> object:
        self._record("delete")
        items = list(self._data)
        value = items.pop(index)
        super().__setattr__("_data", tuple(items))
        return value

    def remove(self, value: object) -> None:
        self._record("delete")
        items = list(self._data)
        items.remove(value)
        super().__setattr__("_data", tuple(items))

    def reverse(self) -> None:
        self._record("reorder")
        super().__setattr__("_data", tuple(reversed(self._data)))

    def sort(self, *args: object, **kwargs: Any) -> None:
        self._record("reorder")
        super().__setattr__("_data", tuple(sorted(self._data, *args, **kwargs)))

    def __iadd__(self, values: Iterable[object]):
        self._record("extend")
        super().__setattr__("_data", (*self._data, *tuple(values)))
        return self

    def __repr__(self) -> str:
        return repr(list(self._data))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Iterable):
            return self._data == list(other)
        return False
