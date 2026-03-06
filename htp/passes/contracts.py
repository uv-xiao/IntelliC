from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from htp.schemas import PASS_CONTRACT_SCHEMA_ID


def _normalize_many(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    return tuple(values or ())


def _validate_path_hint(path_hint: str) -> None:
    path = PurePosixPath(path_hint)
    if path.is_absolute() or ".." in path.parts or not path_hint:
        raise ValueError("analysis path_hint must be a stage-relative path without '..'")


@dataclass(frozen=True)
class AnalysisOutput:
    analysis_id: str
    schema: str
    path_hint: str

    def __post_init__(self) -> None:
        _validate_path_hint(self.path_hint)

    def to_json(self) -> dict[str, str]:
        return {
            "analysis_id": self.analysis_id,
            "schema": self.schema,
            "path_hint": self.path_hint,
        }


@dataclass(frozen=True)
class DiagnosticContract:
    code: str
    payload_schema: str

    def to_json(self) -> dict[str, str]:
        return {
            "code": self.code,
            "payload_schema": self.payload_schema,
        }


@dataclass(frozen=True)
class RunnablePyContract:
    status: str = "preserves"
    modes: tuple[str, ...] = ("sim",)

    def __post_init__(self) -> None:
        if self.status not in {"preserves", "stubbed"}:
            raise ValueError(f"Unsupported runnable_py status: {self.status}")
        if "sim" not in self.modes:
            raise ValueError("Pass contracts must keep stages runnable in sim mode")

    def to_json(self) -> dict[str, object]:
        return {
            "status": self.status,
            "modes": list(self.modes),
        }


@dataclass(frozen=True)
class PassContract:
    pass_id: str
    owner: str
    kind: str
    ast_effect: str
    requires: tuple[str, ...] = field(default_factory=tuple)
    provides: tuple[str, ...] = field(default_factory=tuple)
    invalidates: tuple[str, ...] = field(default_factory=tuple)
    requires_layout_invariants: tuple[str, ...] = field(default_factory=tuple)
    requires_effect_invariants: tuple[str, ...] = field(default_factory=tuple)
    establishes_layout_invariants: tuple[str, ...] = field(default_factory=tuple)
    establishes_effect_invariants: tuple[str, ...] = field(default_factory=tuple)
    analysis_requires: tuple[str, ...] = field(default_factory=tuple)
    analysis_produces: tuple[AnalysisOutput, ...] = field(default_factory=tuple)
    inputs: tuple[str, ...] = field(default_factory=tuple)
    outputs: tuple[str, ...] = field(default_factory=tuple)
    runnable_py: RunnablePyContract = field(default_factory=RunnablePyContract)
    deterministic: bool = True
    diagnostics: tuple[DiagnosticContract, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.kind not in {"analysis", "transform", "mixed"}:
            raise ValueError(f"Unsupported pass kind: {self.kind}")
        if self.ast_effect not in {"preserves", "mutates"}:
            raise ValueError(f"Unsupported ast_effect: {self.ast_effect}")
        if self.kind == "analysis" and self.ast_effect != "preserves":
            raise ValueError("Analysis passes must preserve the AST")
        object.__setattr__(self, "requires", _normalize_many(self.requires))
        object.__setattr__(self, "provides", _normalize_many(self.provides))
        object.__setattr__(self, "invalidates", _normalize_many(self.invalidates))
        object.__setattr__(
            self,
            "requires_layout_invariants",
            _normalize_many(self.requires_layout_invariants),
        )
        object.__setattr__(
            self,
            "requires_effect_invariants",
            _normalize_many(self.requires_effect_invariants),
        )
        object.__setattr__(
            self,
            "establishes_layout_invariants",
            _normalize_many(self.establishes_layout_invariants),
        )
        object.__setattr__(
            self,
            "establishes_effect_invariants",
            _normalize_many(self.establishes_effect_invariants),
        )
        object.__setattr__(self, "analysis_requires", _normalize_many(self.analysis_requires))
        object.__setattr__(self, "analysis_produces", tuple(self.analysis_produces))
        object.__setattr__(self, "inputs", _normalize_many(self.inputs))
        object.__setattr__(self, "outputs", _normalize_many(self.outputs))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    @classmethod
    def analysis(
        cls,
        *,
        pass_id: str,
        owner: str,
        requires: tuple[str, ...] | list[str] | None = None,
        provides: tuple[str, ...] | list[str] | None = None,
        invalidates: tuple[str, ...] | list[str] | None = None,
        analysis_requires: tuple[str, ...] | list[str] | None = None,
        analysis_produces: tuple[AnalysisOutput, ...] | list[AnalysisOutput] | None = None,
        inputs: tuple[str, ...] | list[str] | None = None,
        outputs: tuple[str, ...] | list[str] | None = None,
        deterministic: bool = True,
        diagnostics: tuple[DiagnosticContract, ...] | list[DiagnosticContract] | None = None,
    ) -> "PassContract":
        return cls(
            pass_id=pass_id,
            owner=owner,
            kind="analysis",
            ast_effect="preserves",
            requires=_normalize_many(requires),
            provides=_normalize_many(provides),
            invalidates=_normalize_many(invalidates),
            analysis_requires=_normalize_many(analysis_requires),
            analysis_produces=tuple(analysis_produces or ()),
            inputs=_normalize_many(inputs),
            outputs=_normalize_many(outputs),
            deterministic=deterministic,
            diagnostics=tuple(diagnostics or ()),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema": PASS_CONTRACT_SCHEMA_ID,
            "pass_id": self.pass_id,
            "owner": self.owner,
            "kind": self.kind,
            "ast_effect": self.ast_effect,
            "requires": list(self.requires),
            "provides": list(self.provides),
            "invalidates": list(self.invalidates),
            "requires_layout_invariants": list(self.requires_layout_invariants),
            "requires_effect_invariants": list(self.requires_effect_invariants),
            "establishes_layout_invariants": list(self.establishes_layout_invariants),
            "establishes_effect_invariants": list(self.establishes_effect_invariants),
            "analysis_requires": list(self.analysis_requires),
            "analysis_produces": [output.to_json() for output in self.analysis_produces],
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "runnable_py": self.runnable_py.to_json(),
            "deterministic": self.deterministic,
            "diagnostics": [diag.to_json() for diag in self.diagnostics],
        }


__all__ = [
    "AnalysisOutput",
    "DiagnosticContract",
    "PassContract",
    "RunnablePyContract",
]
