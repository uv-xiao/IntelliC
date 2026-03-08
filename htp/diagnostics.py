from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticCatalogEntry:
    code: str
    title: str
    summary: str
    docs: tuple[str, ...]
    fix_hints: tuple[str, ...]
    fix_hint_policy: str

    def to_explanation(self) -> dict[str, object]:
        return {
            "code": self.code,
            "known": True,
            "title": self.title,
            "summary": self.summary,
            "docs": list(self.docs),
            "fix_hints": list(self.fix_hints),
            "fix_hint_policy": self.fix_hint_policy,
        }


_CATALOG = {
    "HTP.BINDINGS.MISSING_CONTRACT_FILE": DiagnosticCatalogEntry(
        code="HTP.BINDINGS.MISSING_CONTRACT_FILE",
        title="Missing contract artifact",
        summary="A required emitted artifact is absent from the package directory.",
        docs=(
            "docs/design/impls/07_binding_interface.md",
            "docs/design/implementations.md",
        ),
        fix_hints=(
            "Rebuild the package and check the backend emitter wrote every path recorded in manifest.json.",
            "If a new artifact was added, update both the emitter and binding validator together.",
        ),
        fix_hint_policy="rebuild_or_validate_artifacts",
    ),
    "HTP.BINDINGS.MISSING_BACKEND": DiagnosticCatalogEntry(
        code="HTP.BINDINGS.MISSING_BACKEND",
        title="Missing backend target",
        summary="Binding selection requires manifest.target.backend.",
        docs=(
            "docs/design/impls/07_binding_interface.md",
            "docs/design/examples.md",
        ),
        fix_hints=(
            "Emit target.backend during package emission.",
            "Keep manifest target fields aligned with the selected backend binding.",
        ),
        fix_hint_policy="repair_manifest_target_contract",
    ),
    "HTP.REPLAY.STUB_HIT": DiagnosticCatalogEntry(
        code="HTP.REPLAY.STUB_HIT",
        title="Replay hit a stubbed region",
        summary="The stage is runnable in sim, but execution reached an explicitly stubbed region.",
        docs=(
            "docs/design/implementations.md",
            "docs/design/examples.md",
        ),
        fix_hints=(
            "Add sim/reference semantics for the intrinsic or keep the stub as an intentional boundary.",
        ),
        fix_hint_policy="add_sim_semantics_or_accept_stub_boundary",
    ),
}


def explain(code: str) -> dict[str, object]:
    entry = _CATALOG.get(code)
    if entry is not None:
        return entry.to_explanation()
    return {
        "code": code,
        "known": False,
        "title": "Unknown diagnostic code",
        "summary": "No explicit explanation is registered for this diagnostic code yet.",
        "docs": ["docs/design/implementations.md"],
        "fix_hints": ["Inspect the diagnostic payload and package artifacts directly."],
        "fix_hint_policy": "inspect_diagnostic_payload",
    }


__all__ = ["DiagnosticCatalogEntry", "explain"]
