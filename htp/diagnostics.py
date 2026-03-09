from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiagnosticCatalogEntry:
    code: str
    title: str
    summary: str
    docs: tuple[str, ...]
    fix_hints: tuple[str, ...]
    fix_hint_policy: str

    def to_explanation(self, *, matched_by: str = "exact") -> dict[str, object]:
        return {
            "code": self.code,
            "known": True,
            "matched_by": matched_by,
            "title": self.title,
            "summary": self.summary,
            "docs": list(self.docs),
            "fix_hints": list(self.fix_hints),
            "fix_hint_policy": self.fix_hint_policy,
        }


def _entry(
    code: str,
    *,
    title: str,
    summary: str,
    docs: tuple[str, ...],
    fix_hints: tuple[str, ...],
    fix_hint_policy: str,
) -> DiagnosticCatalogEntry:
    return DiagnosticCatalogEntry(
        code=code,
        title=title,
        summary=summary,
        docs=docs,
        fix_hints=fix_hints,
        fix_hint_policy=fix_hint_policy,
    )


_CATALOG = {
    "HTP.BINDINGS.MISSING_CONTRACT_FILE": _entry(
        "HTP.BINDINGS.MISSING_CONTRACT_FILE",
        title="Missing contract artifact",
        summary="A required emitted artifact is absent from the package directory.",
        docs=(
            "docs/design/layers/04_artifacts_replay_debug.md",
            "docs/design/layers/04_artifacts_replay_debug.md",
        ),
        fix_hints=(
            "Rebuild the package and check the backend emitter wrote every path recorded in manifest.json.",
            "If a new artifact was added, update both the emitter and binding validator together.",
        ),
        fix_hint_policy="rebuild_or_validate_artifacts",
    ),
    "HTP.BINDINGS.MISSING_BACKEND": _entry(
        "HTP.BINDINGS.MISSING_BACKEND",
        title="Missing backend target",
        summary="Binding selection requires manifest.target.backend.",
        docs=(
            "docs/design/layers/04_artifacts_replay_debug.md",
            "docs/design/examples/README.md",
        ),
        fix_hints=(
            "Emit target.backend during package emission.",
            "Keep manifest target fields aligned with the selected backend binding.",
        ),
        fix_hint_policy="repair_manifest_target_contract",
    ),
    "HTP.REPLAY.STUB_HIT": _entry(
        "HTP.REPLAY.STUB_HIT",
        title="Replay hit a stubbed region",
        summary="The stage is runnable in sim, but execution reached an explicitly stubbed region.",
        docs=(
            "docs/design/layers/04_artifacts_replay_debug.md",
            "docs/design/layers/01_compiler_model.md",
            "docs/design/layers/04_artifacts_replay_debug.md",
        ),
        fix_hints=(
            "Add sim/reference semantics for the intrinsic or keep the stub as an intentional boundary.",
        ),
        fix_hint_policy="add_sim_semantics_or_accept_stub_boundary",
    ),
}

_FAMILY_CATALOG = (
    (
        "HTP.BINDINGS.PTO_",
        _entry(
            "HTP.BINDINGS.PTO_*",
            title="PTO package or runtime contract issue",
            summary="The PTO binding found an artifact, metadata, build, or runtime mismatch.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/05_backends_and_extensions.md",
                "docs/design/layers/04_artifacts_replay_debug.md",
            ),
            fix_hints=(
                "Check PTO manifest metadata, codegen indices, and emitted toolchain paths together.",
                "If the failure is build/run related, inspect the PTO adapter trace under logs/adapter_pto_*.json.",
            ),
            fix_hint_policy="repair_pto_contract_or_inspect_adapter_trace",
        ),
    ),
    (
        "HTP.BINDINGS.NVGPU_",
        _entry(
            "HTP.BINDINGS.NVGPU_*",
            title="NV-GPU package or runtime contract issue",
            summary="The NV-GPU binding found an artifact, metadata, build, or runtime mismatch.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/05_backends_and_extensions.md",
                "docs/design/layers/04_artifacts_replay_debug.md",
            ),
            fix_hints=(
                "Check the canonical .cu package artifacts, launch metadata, and codegen index together.",
                "If the failure is build/run related, inspect the NV-GPU adapter trace under logs/adapter_nvgpu_*.json.",
            ),
            fix_hint_policy="repair_nvgpu_contract_or_inspect_adapter_trace",
        ),
    ),
    (
        "HTP.BINDINGS.AIE_",
        _entry(
            "HTP.BINDINGS.AIE_*",
            title="AIE package contract issue",
            summary="The AIE binding found a metadata, artifact, or extension-package mismatch.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/05_backends_and_extensions.md",
                "docs/design/layers/04_artifacts_replay_debug.md",
            ),
            fix_hints=("Check the emitted MLIR-AIE package metadata and declared artifact paths together.",),
            fix_hint_policy="repair_aie_artifact_contract",
        ),
    ),
    (
        "HTP.REPLAY.",
        _entry(
            "HTP.REPLAY.*",
            title="Replay or simulator contract issue",
            summary="Stage replay or simulator dispatch hit a stubbed or unsupported execution boundary.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/01_compiler_model.md",
            ),
            fix_hints=(
                "Inspect the stage replay log, replay stubs sidecar, and referenced artifact/toolchain boundary together.",
            ),
            fix_hint_policy="inspect_replay_stub_and_stage_evidence",
        ),
    ),
    (
        "HTP.BINDINGS.",
        _entry(
            "HTP.BINDINGS.*",
            title="Binding contract issue",
            summary="The binding layer found an artifact, schema, entrypoint, or runtime contract problem.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/04_artifacts_replay_debug.md",
            ),
            fix_hints=("Check manifest.json, staged artifacts, and binding validation together.",),
            fix_hint_policy="repair_binding_contract",
        ),
    ),
    (
        "HTP.LAYOUT.",
        _entry(
            "HTP.LAYOUT.*",
            title="Layout legality violation",
            summary="The program’s emitted layout facts conflict with required memory, distribution, or hardware placement rules.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/01_compiler_model.md",
            ),
            fix_hints=(
                "Inspect the staged layout payload and re-check the pass that introduced the conflicting placement or tiling rule.",
            ),
            fix_hint_policy="inspect_layout_payload_and_relayout",
        ),
    ),
    (
        "HTP.EFFECT.",
        _entry(
            "HTP.EFFECT.*",
            title="Effect or synchronization legality violation",
            summary="The program’s effect model has an undischarged async, barrier, or protocol obligation.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/01_compiler_model.md",
            ),
            fix_hints=(
                "Inspect the staged effects payload, pass trace, and protocol checks to find the undischarged obligation.",
            ),
            fix_hint_policy="inspect_effect_payload_and_protocol_checks",
        ),
    ),
    (
        "HTP.TYPECHECK.",
        _entry(
            "HTP.TYPECHECK.*",
            title="Type or alias legality violation",
            summary="The typed semantic layer found a dtype, aliasing, or shape legality violation.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/01_compiler_model.md",
            ),
            fix_hints=("Repair the program’s buffer/view/type contract before backend lowering.",),
            fix_hint_policy="repair_semantic_type_contract",
        ),
    ),
    (
        "HTP.PROTOCOL.",
        _entry(
            "HTP.PROTOCOL.*",
            title="Channel or protocol legality violation",
            summary="The workload/process protocol is unbalanced or otherwise illegal.",
            docs=(
                "docs/design/layers/01_compiler_model.md",
                "docs/design/examples/csp_channel_pipeline.md",
            ),
            fix_hints=("Balance channel puts/gets and re-check process protocol obligations.",),
            fix_hint_policy="repair_protocol_obligations",
        ),
    ),
    (
        "HTP.SOLVER.",
        _entry(
            "HTP.SOLVER.*",
            title="Solver satisfiability failure",
            summary="Pipeline or capability solving could not find a legal composition.",
            docs=(
                "docs/design/layers/04_artifacts_replay_debug.md",
                "docs/design/layers/03_pipeline_and_solver.md",
                "docs/design/layers/04_artifacts_replay_debug.md",
            ),
            fix_hints=(
                "Inspect ir/solver_failure.json and align required outputs, invariants, and providers.",
            ),
            fix_hint_policy="inspect_solver_failure_and_provider_contracts",
        ),
    ),
)


def lookup(code: str) -> tuple[DiagnosticCatalogEntry | None, str]:
    entry = _CATALOG.get(code)
    if entry is not None:
        return entry, "exact"
    for prefix, family_entry in _FAMILY_CATALOG:
        if code.startswith(prefix):
            return family_entry, "family"
    return None, "unknown"


def explain(code: str) -> dict[str, object]:
    entry, matched_by = lookup(code)
    if entry is not None:
        payload = entry.to_explanation(matched_by=matched_by)
        payload["code"] = code
        return payload
    return {
        "code": code,
        "known": False,
        "matched_by": "unknown",
        "title": "Unknown diagnostic code",
        "summary": "No explicit explanation is registered for this diagnostic code yet.",
        "docs": ["docs/design/layers/04_artifacts_replay_debug.md"],
        "fix_hints": ["Inspect the diagnostic payload and package artifacts directly."],
        "fix_hint_policy": "inspect_diagnostic_payload",
    }


def fix_hints_ref_for(code: str) -> str:
    entry, _matched_by = lookup(code)
    if entry is not None and entry.docs:
        return entry.docs[0]
    return "docs/design/layers/04_artifacts_replay_debug.md"


def augment_diagnostic(
    diagnostic: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(diagnostic)
    code = str(payload.get("code", ""))
    explanation = explain(code)
    if "fix_hints_ref" not in payload:
        payload["fix_hints_ref"] = fix_hints_ref_for(code)
    if "payload_ref" not in payload:
        inferred_ref = _infer_payload_ref(payload, manifest=manifest)
        if inferred_ref is not None:
            payload["payload_ref"] = inferred_ref
    if "fix_hint_policy" not in payload:
        payload["fix_hint_policy"] = explanation["fix_hint_policy"]
    return payload


def augment_diagnostics(
    diagnostics: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    manifest: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [augment_diagnostic(dict(item), manifest=manifest) for item in diagnostics]


def _infer_payload_ref(diagnostic: dict[str, Any], *, manifest: dict[str, Any] | None) -> str | None:
    for key in ("trace_ref", "artifact_ref", "program_py"):
        value = diagnostic.get(key)
        if isinstance(value, str):
            return value
    manifest_field = diagnostic.get("manifest_field")
    if isinstance(manifest_field, str):
        return "manifest.json"
    stage_id = diagnostic.get("stage_id")
    if isinstance(stage_id, str) and manifest is not None:
        for stage in manifest.get("stages", {}).get("graph", ()):
            if isinstance(stage, dict) and stage.get("id") == stage_id:
                stage_dir = stage.get("dir")
                if isinstance(stage_dir, str):
                    return stage_dir
    return None


__all__ = [
    "DiagnosticCatalogEntry",
    "augment_diagnostic",
    "augment_diagnostics",
    "explain",
    "fix_hints_ref_for",
    "lookup",
]
