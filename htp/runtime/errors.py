from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_STUB_REASON_BY_CODE = {
    "HTP.REPLAY.STUB_HIT": "intentionally_unimplemented",
    "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC": "missing_simulator",
    "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY": "external_toolchain_only",
}

_STUB_FIX_HINTS_BY_CODE = {
    "HTP.REPLAY.STUB_HIT": (
        "Implement replay semantics for the stubbed region or regenerate the stage with a supported simulator.",
    ),
    "HTP.REPLAY.STUB_UNSUPPORTED_INTRINSIC": (
        "Register a simulator for the intrinsic in the replay runtime.",
        "Route replay through an owning extension if simulation is toolchain-specific.",
    ),
    "HTP.REPLAY.STUB_EXTERNAL_TOOLCHAIN_ONLY": (
        "Replay through the owning extension or binding.",
        "Inspect the emitted backend artifacts referenced by the stub.",
    ),
}


class ReplayDiagnosticError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        payload: Mapping[str, Any] | None = None,
        fix_hints: Sequence[str] = (),
    ) -> None:
        self.code = code
        self.payload = dict(payload or {})
        self.fix_hints = tuple(fix_hints)
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        detail = self.payload.get("detail")
        if detail:
            return f"{self.code}: {detail}"
        node_id = self.payload.get("node_id")
        if node_id:
            return f"{self.code}: node_id={node_id}"
        return self.code


def raise_stub(
    code: str,
    *,
    node_id: str,
    entity_id: str | None = None,
    kind: str,
    artifact_ref: str | None = None,
    detail: str | None = None,
) -> None:
    fix_hints = _STUB_FIX_HINTS_BY_CODE.get(code, _STUB_FIX_HINTS_BY_CODE["HTP.REPLAY.STUB_HIT"])
    payload: dict[str, Any] = {
        "node_id": node_id,
        "kind": kind,
        "reason": _STUB_REASON_BY_CODE.get(code, "intentionally_unimplemented"),
        "next_actions": list(fix_hints),
    }
    if entity_id is not None:
        payload["entity_id"] = entity_id
    if artifact_ref is not None:
        payload["artifact_ref"] = artifact_ref
    if detail is not None:
        payload["detail"] = detail
    raise ReplayDiagnosticError(code, payload=payload, fix_hints=fix_hints)


__all__ = ["ReplayDiagnosticError", "raise_stub"]
