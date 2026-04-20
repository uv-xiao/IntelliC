# Compiler Framework Source Reading Report

- **Date**: 2026-04-20
- **Purpose**: Ground the clean IntelliC compiler framework design in MLIR, xDSL,
  and the previous `origin/htp/v0` architecture without importing legacy
  implementation shape.

## Sources

- `.repositories/llvm-project` at `f2efeabe3`
- `.repositories/xdsl` at `d875f35`
- `.references/acm-3729331.pdf` downloaded from the author-hosted PDF for DOI
  `10.1145/3729331` after the ACM PDF endpoint returned HTTP 403
- `.repositories/egg` at `f94c346`
- `.repositories/egglog` at `b27cd22`
- `origin/htp/v0`
- `docs/story.md`
- `docs/design/agent_harness.md`

## Source Scope Map

| Source | Scope Read | Useful Shape | IntelliC Use |
| --- | --- | --- | --- |
| MLIR LangRef | Operations, blocks, regions, dialects, attributes, types | Uniform extensible IR syntax | `Sy` object model |
| MLIR operation definitions | ODS, traits, operands, results, verification | Single operation record as source of truth | `OpDef` syntax and verifier contract |
| MLIR attributes/types docs | Open type system, immutable value-typed attributes/types | Explicit compile-time data and value typing | `Type` and `Attribute` contracts |
| xDSL IR core | Python `Operation`, `Region`, `Block`, `Attribute` classes | Python-native MLIR-style syntax | IntelliC Python-native IR objects |
| xDSL parser/printer | MLIR-compatible generic/custom operation syntax | Existing Python `ir_parser` shape | Native IntelliC `ir_parser` copied/adapted from xDSL |
| xDSL interpreter | Operation implementation dispatch and execution trace hooks | Executable operation behavior | `Se` semantics functions |
| xDSL eqsat docs/transforms | E-class insertion, PDL-interp eqsat rewrites, costs, extraction | E-graph pipeline embedded in IR | Equality reasoning as an action/model |
| Fjfj PLDI 2025 paper | Rule/method semantics, partial transition relations, modular verification | Trace-updating semantics with restrictions | `Se` trace model and modular semantic domains |
| egg | E-graphs, rewrites, analyses, cost functions, extraction, explanations | Equality saturation core ideas | Possible backend/model for equivalence actions |
| egglog | Datalog-style equality saturation, relations, schedules, extraction | Relational/action-oriented saturation | Possible backend/model for trace/e-graph actions |
| `origin/htp/v0` docs/code | Python surfaces, replay, typed semantic state | Human/agent-friendly artifacts | Surface and evidence requirements |

## Visual Model

```text
Lang
  |
  +--> Surface
  |      |
  |      `--> Parser
  |             |
  |             v
  |            IR
  |
  `--> IR
         |
         +--> Sy  syntax: Operation, Region, Block, Type, Attribute
         `--> Se  semantics: run behavior, effects, obligations, evidence
```

## Compiler Flowchart

```mermaid
flowchart LR
    A[Pythonic Surface] --> B[Surface Parser]
    B --> C[Canonical IR Text]
    C --> D[IR Parser]
    D --> E[Sy Objects]
    E --> F[Semantic Models]
    F --> G[Compiler Actions]
    G --> H[Trace and Evidence]
```

## Parser Split

```text
surface_parser:
  many modular frontends
  accepts human/LLM-friendly source forms
  shares source capture, diagnostics, and lowering helpers
  emits canonical IR plus source evidence

ir_parser:
  one canonical parser family
  copied/adapted from xDSL's parser/printer
  strictly follows MLIR/xDSL generic and custom operation syntax
```

## Code Sketches

Operation syntax should use real MLIR-style dialect names:

```mlir
"builtin.module"() ({
  func.func @add_one(%x: i32) -> i32 {
    %c1 = arith.constant 1 : i32
    %y = arith.addi %x, %c1 : i32
    func.return %y : i32
  }
}) : () -> ()
```

Surface parser contract:

```python
parsed = parse_surface(add_one)
assert parsed.ir_text == expected_ir
assert parsed.report.source_spans["x + 1"].op_name == "arith.addi"
assert roundtrip(parsed.ir).semantic_hash == parsed.ir.semantic_hash
```

General semantic trace sketch:

```text
(syntax, facts_in, trace_in) relation (facts_out, trace_out)

trace events may include:
  execution events
  abstract facts
  effect facts
  obligation-like facts
  diagnostics
  e-graph saturation evidence
  backend evidence
  LLM-agent review notes
```

E-graph action sketch:

```text
IR fragment
  -> e-class/e-node facts
  -> rewrite/rule schedule
  -> saturated graph
  -> cost-based extraction
  -> replacement IR plus evidence trace
```

## Source Comparison

| Concern | MLIR | xDSL | v0 | IntelliC Decision |
| --- | --- | --- | --- | --- |
| Syntax owner | Dialect operations | Python operation classes | Custom typed payloads | MLIR/xDSL-derived `Sy` |
| Semantics owner | Traits/interfaces plus pass conventions | Interpreter implementations | Interpreter and semantic payloads | Polymorphic `Se` models over syntax and trace |
| Human surface | Textual IR and dialect custom assembly | Python APIs and notebooks | Pythonic authoring and staged Python | `Surface := IR + Parser` |
| Equality reasoning | Pattern rewrites | Embedded eqsat transforms | Not central | E-graph/equality-saturation action model |
| Evidence | Round-trip text and lit tests | pytest/lit examples | staged artifacts and replay | Examples become tests or evidence |
| Extensibility | Dialects | Dialects and operation classes | Dialects/frontends | Dialects cannot bypass `Sy + Se` verification |

## Semantics Reference Lessons

| Source | Lesson For IntelliC |
| --- | --- |
| xDSL interpreter | Concrete execution can dispatch by operation implementation, but IntelliC should generalize beyond one interpreter hook. |
| Fjfj paper | Modular semantics may require language restrictions and trace structures so behavior can be characterized one method/rule at a time instead of by exponential concurrent combinations. |
| egg | Equality reasoning should be handled by e-graphs, rewrites, analyses, costs, extraction, and explanations. |
| egglog | A relational rules/schedule model can combine equality saturation with Datalog-style facts and incremental analyses. |
| xDSL eqsat | E-classes can be embedded into IR, rewrites can be applied non-destructively, costs can be attached, and extraction can produce a chosen program. |

## Decision Trace

```text
Need human-friendly authoring
  -> keep modular Surface parsers
Need agent-friendly review
  -> require canonical IR text, examples, and traces
Need MLIR ecosystem alignment
  -> strictly match MLIR/xDSL syntax and copy/adapt xDSL classes
Need missing MLIR semantics gap closed
  -> make polymorphic Se models and traces first-class
Need transform equivalence
  -> explore egg/egglog/xDSL eqsat instead of per-op equivalence fields
Need pass simplicity
  -> unify analysis/rewrite/pass/gate/execution/LLM review as actions
```

## Extracted Lessons

- MLIR's strongest reusable idea is its uniform syntax model: dialects own
  operations, and operations uniformly contain operands, results, successors,
  properties, attributes, and regions.
- MLIR regions make nested program structure explicit while leaving region
  semantics to the containing operation. This is a useful split for IntelliC because
  scheduling, graph, and control-flow regions should not be forced into one
  execution model.
- MLIR ODS keeps operation facts in one declarative record for documentation,
  building, parsing, printing, verification, and tooling. IntelliC should preserve
  the "one operation specification" idea, but extend it with executable
  semantics.
- MLIR attributes and types are open extension points. IntelliC should keep them
  immutable and explicit enough for round-trip text, tests, and agent review.
- xDSL shows that the MLIR syntax model can live ergonomically in Python, with
  `Operation`, `Region`, `Block`, `Attribute`, and `TypeAttribute` classes.
- xDSL's interpreter shows a practical shape for executable semantics:
  implementation functions dispatch by operation type, receive Python runtime
  values for operands, and return Python runtime values for results. IntelliC should
  use that as one semantic model, not as the only semantic shape.
- The Fjfj paper shows that semantic modularity may come from a combination of
  restrictions, partial transition relations, and tracked calls/events. IntelliC
  should consider general trace-updating semantics before freezing specific
  effect or obligation fields.
- egg and egglog show that equivalence should be a saturation mechanism with
  rules, analyses, schedules, cost models, extraction, and explanations rather
  than a field on each operation's semantics.
- xDSL's eqsat implementation shows an IR-embedded equality-saturation flow:
  create e-classes, apply PDL-derived rewrites non-destructively, add costs, and
  extract the chosen program.
- xDSL's developer docs prefer small examples plus lit/pytest evidence. This
  matches the IntelliC harness rule that design examples must become tests or
  evidence.
- `origin/htp/v0` proves that human-readable Python surfaces, staged artifacts,
  replay, typed semantic state, and interpreter-backed execution make compiler
  work easier for humans and agents. The clean design should keep those goals
  while replacing the custom v0 syntax substrate with an MLIR/xDSL-derived one.
- v0 also shows a risk: if semantics live as scattered metadata payloads,
  examples become hard to inspect and tests become indirect. The clean design
  should define `Se` next to `Sy` for every operation.

## Decisions Affected

- Define IntelliC's core principle as compiler participation by both human
  programmers and LLM agents.
- Treat `Surface` and `IR` as the practical concepts; keep `Lang` only as a
  classification term.
- Define `Surface := IR + Parser`, where the parser maps a friendly Pythonic
  authoring form into canonical IR.
- Split parsing into modular `surface_parser` infrastructure and a strict
  MLIR/xDSL-compatible `ir_parser`.
- Define `IR := Sy + Se`, with MLIR/xDSL-derived syntax plus first-class
  polymorphic semantic models.
- Copy/adapt selected xDSL syntax and parser classes into native IntelliC instead of
  exposing wrappers around upstream xDSL modules.
- Use existing dialect names such as `builtin`, `func`, and `arith` in examples;
  IntelliC is not itself a dialect.
- Treat effects, obligations, diagnostics, and agent review as trace facts until
  examples prove a dedicated abstraction is required.
- Explore egg, egglog, and xDSL eqsat before designing equivalence mechanisms.
- Use concrete examples as design contracts and require each one to map to an
  automated test or named evidence artifact.

## Follow-Up Evidence

- Parser evidence should cover both surface parsing and strict IR parsing.
- Round-trip evidence should parse, print, and reparse canonical IR without
  semantic hash changes.
- Semantics evidence should show multiple models can apply to one operation.
- Trace evidence should show effects/obligations/diagnostics as general facts.
- E-graph evidence should compare egg, egglog, and xDSL eqsat integration paths.
- Pass evidence should show analysis, rewrite, gate, semantic execution, and
  LLM-agent review as unified actions.
