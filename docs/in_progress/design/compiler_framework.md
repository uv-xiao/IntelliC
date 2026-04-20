# Design: Compiler Framework

> Review status: Draft only. Not reviewed or approved. This document records
> current working direction and fix advice for IntelliC; do not treat it as
> accepted architecture until explicit human review approves it.

## Goal

IntelliC is an intelligent compiler infrastructure for both human programmers and
LLM agents. Its compiler core must be strong enough to support future compiler
construction above it: new programming surfaces, new IR levels, new dialects,
new semantic domains, new analyses, new transforms, new backends, and
agent-readable evidence.

The framework starts from these concepts:

```text
Lang := Surface | IR
Surface := IR + Parser
IR := Sy + Se
```

`Lang` is a classification term. Most code and docs should talk directly about
`Surface` or `IR` because they have different contracts.

## Decision

Pick **C. MLIR/xDSL-Derived Syntax Plus First-Class IntelliC Semantics**.

IntelliC will define a Python-native compiler infrastructure whose IR syntax strictly
matches MLIR/xDSL textual structure, while semantics, analysis, transform, and
pipeline mechanisms are designed as first-class IntelliC contracts. This is the
durable direction for the clean branch.

The selected split is:

- `Sy`: syntax, structure, identity, verification, canonical MLIR/xDSL-style
  text, and IR parsing.
- `Se`: polymorphic semantic models over syntax, expressed through transition
  and trace mechanisms where possible.
- Pipeline infrastructure: a unified action mechanism for parsing, analysis,
  rewriting, semantic execution, gates, LLM-agent steps, and backend handoff.

## Parser Split

IntelliC needs two parser families:

```text
surface_parser:
  modular parsers for human/LLM-facing programming surfaces
  each parser lowers into canonical IR and produces source evidence

ir_parser:
  strict MLIR/xDSL-style parser for canonical IR text
  based on xDSL's existing Python parser, copied into native IntelliC and adjusted
  only where IntelliC architecture requires it
```

Surface parsers should be modular but share common infrastructure: source
capture, diagnostics, symbol binding, lowering utilities, example evidence, and
round-trip hooks. The IR parser has a different contract: it must parse the
canonical IR syntax accepted by MLIR/xDSL, including generic and custom
operation forms.

## Design Decomposition

This umbrella document records the architectural choice and links the concrete
subdesigns:

- `docs/in_progress/design/compiler_syntax.md` — `Sy`, copied/adapted from
  xDSL classes where useful, with strict MLIR/xDSL syntax format and separate
  `surface_parser` / `ir_parser` contracts.
- `docs/in_progress/design/compiler_semantics.md` — `Se`, designed as
  polymorphic semantic models and trace-updating transition systems rather than
  a single semantic definition per operation.
- `docs/in_progress/design/compiler_passes.md` — unified compiler actions for
  analysis, rewrite, pass, gate, semantic execution, LLM-agent participation,
  and backend handoff.

The child docs own detailed contracts. This file should not duplicate those
contracts beyond the cross-cutting requirements below.

## Framework Shape

Planned package ownership:

```text
intellic/
  ir/
    syntax/          # copied/adapted xDSL-style Operation, Region, Block, etc.
    semantics/       # semantic models, transition relations, trace updates
    actions/         # unified analysis/rewrite/pass/gate/action execution
    dialects/        # dialect registration and extension ownership
    parser/          # ir_parser: strict canonical IR parser
  surfaces/
    parser/          # surface_parser shared infrastructure and modular parsers
  examples/          # small executable examples used as evidence
```

Core dependency direction:

```text
surface_parser modules
      |
      v
canonical IR text <----> ir_parser
      |
      v
  Sy objects  <---- dialect definitions
      |
      v
  Se models and trace updates
      |
      v
Unified compiler actions
      |
      v
Evidence: source maps, traces, e-graphs, artifacts, review notes
```

`Sy` owns structural shape and MLIR/xDSL-compatible syntax. `Se` depends on
`Sy`, but it must not be hidden inside parser or action-local metadata. Compiler
actions depend on both `Sy` and `Se` and record their changes in a general trace
or evidence stream.

## Cross-Cutting Contracts

- Every canonical IR program is `IR := Sy + Se`, not syntax alone.
- `surface_parser` and `ir_parser` are different parser families with shared
  lower-level infrastructure where useful.
- `ir_parser` must strictly match MLIR/xDSL canonical syntax.
- Native IntelliC syntax classes are copied/adapted from xDSL where useful; they are
  not imported through wrappers as IntelliC's public architecture.
- IntelliC is the infrastructure name, not a dialect name. Examples should use
  MLIR-style dialect names such as `builtin`, `func`, and `arith`, or future
  real project dialect names once designed.
- A single operation may have multiple semantic models, such as concrete
  execution, abstract interpretation, rewrite/equality reasoning, or backend
  evidence semantics.
- Effects, obligations, diagnostics, and pass gates should be represented as
  general trace facts or evidence records unless a later design proves a more
  specific abstraction is necessary.
- Compiler pipeline pieces should share one action mechanism where possible;
  analysis, rewrite, pass, gate, semantic execution, and LLM-agent review are
  specializations of action execution rather than unrelated subsystems.
- Every design example maps to evidence before implementation starts. For
  documentation-only work, evidence may be a focused reread, link/path check,
  or policy check rather than automated tests.

## Examples

### Example 1: One Feature Crosses All Subsystems

Surface:

```python
@surface
def add_one(x: i32) -> i32:
    return x + 1
```

Canonical IR sketch:

```mlir
"builtin.module"() ({
  func.func @add_one(%x: i32) -> i32 {
    %c1 = arith.constant 1 : i32
    %y = arith.addi %x, %c1 : i32
    func.return %y : i32
  }
}) : () -> ()
```

Decomposition:

```text
surface_parser:
  lower Pythonic source to canonical IR plus source evidence

ir_parser:
  parse strict MLIR/xDSL-style canonical text

compiler_syntax.md:
  define copied/adapted Operation, Region, Block, Value, Type, Attribute classes

compiler_semantics.md:
  attach one or more semantic models to builtin/func/arith operations

compiler_passes.md:
  run unified actions for interpretation, rewriting, eqsat, gates, and review
```

Verification mapping: parser golden evidence, IR round-trip evidence, semantic
trace evidence, and action-pipeline evidence.

### Example 2: E-Graph Reasoning Is A Mechanism, Not Per-Op Equivalence Fields

Rewrite family:

```text
arith.addi(%x, %zero) <=> %x
arith.muli(%x, %one)  <=> %x
```

Feature shown: equivalence belongs in an equality-saturation/e-graph mechanism
that can consume rewrite rules and cost models. Operation semantics do not need
per-op equivalence fields.

Verification mapping: e-graph action evidence records e-class creation,
saturation rules, extraction cost, and chosen replacement.

## Acceptance Criteria

- `compiler_framework.md` records only the selected architectural decision,
  parser split, decomposition, and cross-cutting requirements.
- Syntax, semantics, and pass mechanisms each have focused design drafts.
- The syntax design avoids declarative operation-definition machinery as an
  initial dependency, distinguishes `surface_parser` and `ir_parser`, and
  commits to strict MLIR/xDSL syntax.
- The semantics design allows multiple semantic models per operation and treats
  effects/obligations/diagnostics/traces as general trace facts until proven
  otherwise.
- The passes design unifies pass, analysis, rewrite, gates, semantic execution,
  and LLM-agent pipeline participation around one action mechanism.

## Out Of Scope

- Direct implementation of the compiler core.
- Designing a complete surface language.
- Backend lowering details beyond semantic/evidence boundaries.
- Treating `intellic` as a dialect name before dialect design exists.

## Closeout

When implemented, promote the umbrella and child designs into `docs/design/`,
update `docs/todo/README.md`, and remove completed in-progress drafts.
