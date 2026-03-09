from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class CompilerDiagnosticError(ValueError):
    code: str
    detail: str
    node_id: str | None = None
    entity_id: str | None = None
    stage_id: str | None = None
    pass_id: str | None = None
    payload_ref: str | None = None
    payload_ref_hint: str | None = None
    fix_hints_ref: str | None = None
    fix_hints: tuple[str, ...] = ()
    extra: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        ValueError.__init__(self, self._format_message())

    def with_context(self, **updates: Any) -> CompilerDiagnosticError:
        payload = {
            "code": self.code,
            "detail": self.detail,
            "node_id": self.node_id,
            "entity_id": self.entity_id,
            "stage_id": self.stage_id,
            "pass_id": self.pass_id,
            "payload_ref": self.payload_ref,
            "payload_ref_hint": self.payload_ref_hint,
            "fix_hints_ref": self.fix_hints_ref,
            "fix_hints": self.fix_hints,
            "extra": dict(self.extra),
        }
        payload.update(updates)
        extra = payload.pop("extra", {})
        return replace(
            self,
            extra=tuple(sorted(dict(extra).items())),
            **{key: value for key, value in payload.items() if key != "fix_hints"},
            fix_hints=tuple(payload.get("fix_hints", self.fix_hints)),
        )

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "detail": self.detail,
        }
        if self.node_id is not None:
            payload["node_id"] = self.node_id
        if self.entity_id is not None:
            payload["entity_id"] = self.entity_id
        if self.stage_id is not None:
            payload["stage_id"] = self.stage_id
        if self.pass_id is not None:
            payload["pass_id"] = self.pass_id
        if self.payload_ref is not None:
            payload["payload_ref"] = self.payload_ref
        if self.fix_hints_ref is not None:
            payload["fix_hints_ref"] = self.fix_hints_ref
        if self.fix_hints:
            payload["fix_hints"] = list(self.fix_hints)
        payload.update(dict(self.extra))
        return payload

    def _format_message(self) -> str:
        if self.pass_id is not None:
            return f"{self.code} at {self.pass_id}: {self.detail}"
        return f"{self.code}: {self.detail}"


def compiler_error(
    code: str,
    detail: str,
    *,
    node_id: str | None = None,
    entity_id: str | None = None,
    payload_ref_hint: str | None = None,
    fix_hints_ref: str | None = None,
    fix_hints: Sequence[str] = (),
    **extra: Any,
) -> CompilerDiagnosticError:
    return CompilerDiagnosticError(
        code=code,
        detail=detail,
        node_id=node_id,
        entity_id=entity_id,
        payload_ref_hint=payload_ref_hint,
        fix_hints_ref=fix_hints_ref,
        fix_hints=tuple(fix_hints),
        extra=tuple(sorted(extra.items())),
    )


def failure_payload(
    *,
    pass_id: str,
    stage_before: str | None,
    diagnostic: CompilerDiagnosticError,
) -> dict[str, Any]:
    return {
        "schema": "htp.compiler_failure.v1",
        "failed_at_pass": pass_id,
        "stage_before": stage_before,
        "diagnostic": diagnostic.to_json(),
    }


__all__ = ["CompilerDiagnosticError", "compiler_error", "failure_payload"]
