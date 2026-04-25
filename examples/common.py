from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ExampleRun:
    name: str
    canonical_ir: str
    parse_print_idempotent: bool
    semantic_result: tuple[object, ...] | None = None
    semantic_records: Mapping[str, int] = field(default_factory=dict)
    action_names: tuple[str, ...] = ()
    relation_counts: Mapping[str, int] = field(default_factory=dict)
    mutation_applied_count: int = 0
    mutation_rejected_count: int = 0
    final_ir: str | None = None
    documented_gaps: tuple[str, ...] = ()


def print_example_run(run: ExampleRun) -> str:
    lines = [
        f"== {run.name} ==",
        "",
        "canonical_ir:",
        run.canonical_ir,
        "",
        f"parse_print_idempotent: {str(run.parse_print_idempotent).lower()}",
    ]
    if run.semantic_result is not None:
        lines.append(f"semantic_result: {run.semantic_result}")
    if run.semantic_records:
        lines.append("semantic_records:")
        lines.extend(f"  {key}: {value}" for key, value in sorted(run.semantic_records.items()))
    if run.action_names:
        lines.append(f"actions: {', '.join(run.action_names)}")
    if run.relation_counts:
        lines.append("relation_counts:")
        lines.extend(f"  {key}: {value}" for key, value in sorted(run.relation_counts.items()))
    lines.append(f"mutation_applied_count: {run.mutation_applied_count}")
    lines.append(f"mutation_rejected_count: {run.mutation_rejected_count}")
    if run.final_ir is not None:
        lines.extend(("", "final_ir:", run.final_ir))
    if run.documented_gaps:
        lines.append("documented_gaps:")
        lines.extend(f"  - {gap}" for gap in run.documented_gaps)
    return "\n".join(lines) + "\n"
