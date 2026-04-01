from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_payload(value: Any) -> Any:
    if is_dataclass(value):
        return to_payload(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_payload(item) for item in value]
    return value


__all__ = ["to_payload"]
