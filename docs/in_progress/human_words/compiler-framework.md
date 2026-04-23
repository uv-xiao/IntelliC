# Human Words: Compiler Framework

## Category

- Primary: Compiler Framework

## Timeline

- 2026-04-21 02:12 Asia/Shanghai - Core compiler concepts and references
  > 0. Lang (language): form of a program, either at the programming surface (or original inputs), or at an intemediate level. That is Lang := Surface | IR.
  >   We don't frequently use this concept in ICI. Instead, we use Surface and IR for specific siturations, since they have different requirements.
  >
  >   1. Sur (programming surface): this is what human/LLM programs. It somehow can be defined as: Sur := IR + Parser, where Parser can transform a pretty,
  >   human-friendly, Pythonic form into IR data structure.
  >
  >   2. IR (intemediate representation): what operations look like and what they mean (or how they run). We define them as IR := Sy + Se.
  >
  >   3. Sy (syntax): what operations look like. We derive the IR system from MLIR (you should clone into .repositories) and xDSL (same IR system as MLIR, also
  >   need to be cloned). It include Operation, Region, Type, Attribute.
  >
  >   4. Se (semantics): what operations mean, or how they run. This is what MLIR and xDSL missed. We need to provide a mechanism to define how operation runs.
  >
  >   dev/v0 generally share the same idea, but we don't use MLIR/xDSL's syntax there. But it helps us to build the new design. Let's do the design from scratch
  >   with all references well studied.
  - Context: User defined the first-principles compiler framework concepts and reference-reading expectations for the clean design.
  - Related: docs/in_progress/compiler_framework.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/in_progress/design/compiler_syntax.md
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Treat `Lang`, `Surface`, `IR`, `Sy`, and `Se` as the conceptual basis, use MLIR/xDSL for syntax learning, and design IntelliC semantics from scratch with references studied.

- 2026-04-21 02:13 Asia/Shanghai - Compiler design fix advice
  > - docs/in_progress/design/compiler_framework.md: 
  >   1. surface parser should also be modular, but can share a common infrastructure. We need two parsers: surface_parser and ir_parser; the latter one is existing in xDSL already.
  > - docs/in_progress/design/compiler_syntax.md:
  >   1. We don't need IRDL things.
  >   2. distinguish surface_parser and ir_parser.
  >   3. We don't wrappers to import xDSL things. We just copy the xDSL classes into native ICI, and modify them to meet ICI's architecture requirements.
  >   4. don't use things like `ici.xxx`, ici is not a dialect. use `builtin` (or look at mlir to see how it uses)
  >   5. strictly match syntax format with MLIR and xDSL.
  > - docs/in_progress/design/compiler_semantics.md: 
  >   1. It's essential to think about how semantics can enable.
  >   2. The SemanticDef is too complicated. For example, execute and abstract can be two SemanticDef for one operation, we should consider this capability about polymorphism in ICI. So abstract interpretation is not a seperate layer.
  >   3. Not sure if we need to make effect, obligation, diagnostics, trace_events, value_store, resource_state, all specific. In my mind, they can all be processed in a general way, may be just as a trace. And we need mechanism to define or program how trace is updated, like formal models (operatinal semantics?) in PL (not sure about this). One possible reference is (https://dl.acm.org/doi/pdf/10.1145/3729331, you should download to .references/).  We need more discussion about this, with experiences learned from existing projects.
  >   4. For equivalence, it looks cool. But we can think about absorbing eqsat things. You should clone egg (https://github.com/egraphs-good/egg) and egglog (https://github.com/egraphs-good/egglog) projects into .repositories. Also, see xDSL's eqsat support (.repositories/xdsl/xdsl/transforms/eqsat*.py and .repositories/xdsl/docs/marimo/eqsat.py). If we have this mechanism, we don't need to define equivalance for operations' semantics.
  >   5. We don't need to consider things like `ici.if`, we just import (copy and adjust) things from xdsl/mlir.
  >   6. "Every non-opaque operation has one `SemanticDef`" doens't hold.
  > - docs/in_progress/design/compiler_passes.md: 
  >   1. we've discussed about complexity under semantics design. I noticed that our design have obligations or semantic capabilities for Pass. We need to make them consistent: maybe a very general effect trace system for both.
  >   2. I think pass/analysis/rewrite shouldn't be so different and specific. They should share as much as possible. This could make architecture/implementation easier. For example, Pass is more flexible rewrite pattern, where the matcher is simple and applier is general C++/python manipulations. We should try to unify them. Also, gates are not special, either. It should also be unified.
  >   3. We need to be fully prepared about using semantic execution and LLM agents during the pass pipeline. These are major features and overlooked now.
  - Context: User provided document-specific correction advice for the in-progress compiler framework, syntax, semantics, and pass drafts.
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/in_progress/design/compiler_syntax.md
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_passes.md
  - Agent interpretation: Keep parser families distinct, avoid IRDL and wrapper-based xDSL imports, use MLIR/xDSL-compatible syntax and real dialect names, support polymorphic semantic models, use general trace mechanisms, absorb eqsat ideas, and unify pass/analysis/rewrite/gate/action infrastructure with semantic execution and LLM pipeline participation.

- 2026-04-22 13:24 local - Surface design pivot to construction APIs
  > i regret about the design, since do parser level conposition is very hard. Instead, we can define high level APIs or primitives to construct IR, not through parsing. This should also give near native python programming experience without playing woth a new larser mechanism.
  - Context: User corrected the in-progress syntax/surface parser design direction during design continuation.
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/in_progress/design/compiler_syntax.md
  - Agent interpretation: Replace parser-level composition as the primary surface mechanism with composable high-level Python IR construction APIs/primitives that provide near-native Python authoring while avoiding a new parser mechanism.

- 2026-04-22 13:51 local - Larger first syntax slice
  > i think syntaz things are easy since we can just learn how xdsl does. So we should make the first slice large.
  - Context: User corrected the scope of the first syntax implementation slice during design continuation.
  - Related: docs/in_progress/design/compiler_syntax.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Agent interpretation: Because syntax can be copied/adapted from xDSL, the first syntax implementation slice should include a broader xDSL-derived object/parser/printer/dialect/builder substrate instead of a very small builder-only slice.

- 2026-04-22 14:44 local - Trace as semantic database
  > it should be a shared semantic state/fact/event db.
  - Context: User clarified the semantics design direction after discussing whether Trace is only a log or a shared semantic state.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_passes.md
  - Agent interpretation: Design Trace as the shared semantic database for state, facts, events, diagnostics, evidence, and projections; ordered events are one component, not the whole model.

- 2026-04-22 14:50 local - Simplify TraceDB design
  > should we simplify the things in a trace? there more much redindancy (in my mind). you should do a careful analysis to decide how to unify and what to keep.
  - Context: User requested careful semantics design analysis of TraceDB redundancy and simplification.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_passes.md
  - Agent interpretation: Analyze TraceDB fields for redundancy, unify overlapping concepts, and keep only the minimal primitive record kinds needed for semantic state, facts, events, diagnostics, evidence, and projections.

- 2026-04-22 15:01 local - Prioritize semantic definition architecture
  > before making semantics complete, we need a more high-level design first. one concrete design is how we should define semantics for specifoc IR or an operation. This is very important, We should design this first before refining more semantic details.
  - Context: User redirected semantics work toward the high-level mechanism for defining semantics for an IR or operation before refining TraceDB details.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Agent interpretation: Design the authoring and registration model for semantic definitions first: how an IR, dialect, region convention, or operation contributes semantic models and capabilities over TraceDB.

- 2026-04-22 15:20 local - Thin semantic definition model
  > i think we introduce too many concepts for the semantic definition. We should design that thin. you should give very concise example , and it should reflect multi-level semantic def (concrete value, abstract).
  - Context: User requested simplifying the semantic definition authoring model after reviewing SemanticPackage/Profile/Capability concepts.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Agent interpretation: Replace heavyweight semantic packages/profiles/capabilities with a thinner level-tagged semantic definition registry and concise examples for concrete value and abstract semantics.

- 2026-04-22 15:33 local - Bind semantic definitions to operations
  > i think the semantic def should be bound to operations tightly, just as how mlir/xdsl do for syntax. btw, we need to avoid using stringref for registration.
  - Context: User refined the thin SemanticDef design, emphasizing tight operation binding and typed registration instead of string-based lookup.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_syntax.md
  - Agent interpretation: Semantic definitions should be declared on or near typed operation/dialect classes and registered by typed operation/dialect/level keys, not by string names.

- 2026-04-22 16:06 local - Add tiny operation semantic examples
  > lets give some clear tiny but mighty examples. for very example, we consider how the semantica are defined for operations.
  - Context: User requested clearer small examples for operation-bound semantic definitions.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Agent interpretation: Add concise examples showing how individual operations define multiple semantic levels through typed operation-owned SemanticDef records.

- 2026-04-22 16:41 local - Explain semantic polymorphism and interpreter generation
  > explian how polymorphisim is supported for semantic defination. Also, explain if semantic definition can generate an intepreter and how.
  - Context: User asked to clarify polymorphism for operation-bound SemanticDef records and whether those definitions can generate an interpreter.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_passes.md
  - Agent interpretation: Document typed owner/level polymorphism, fallback resolution, conflict rules, and interpreter generation from selected concrete semantic definitions.

- 2026-04-22 17:15 local - Compare semantics with Fjfj trace semantics
  > good. also compare with the hjhj paper's trace based semantic
  - Context: User asked to compare IntelliC semantic definitions and TraceDB with the previously referenced Fjfj paper trace-based semantics. Interpreting hjhj as Fjfj from the active source notes.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Add a concise comparison explaining which Fjfj trace-based semantics ideas IntelliC adopts, adapts, or keeps out of scope.

- 2026-04-23 00:51 local - Link syntax design to xDSL references
  > In docs/in_progress/design/compiler_syntax.md , we need to add links to the reference xdsl design if existing. This covers most parts of compiler syntax since we borrow most syntax from xdsl/mlir.
  - Context: User requested explicit references from the syntax design to xDSL/MLIR sources because IntelliC syntax borrows heavily from them.
  - Related: docs/in_progress/design/compiler_syntax.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Add a reference map in the syntax design that points readers to the local xDSL and MLIR source/docs used as the basis for syntax classes, parser/printer, dialects, and tests.

- 2026-04-23 12:42 local - Model e-graph rewrite as operations
  > One thing wrong about the docs/in_progress/design/compiler_semantics.md is that the e-graph rewrite model should not be modeled at the semantic level; Similar to eqsat's solution, it can be modeled as operations.
  - Context: User corrected the semantics design: e-graph rewrite/eqsat should not be a SemanticDef level, but should be represented through IR operations/actions similar to xDSL eqsat.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_passes.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Remove EGraph as a semantic level/model and describe equality saturation as operation-modeled IR/action infrastructure with TraceDB evidence.

- 2026-04-23 12:45 local - Make semantic levels extensible and selectable
  > For semantic definition, the level should not be fixed variants. It should be flexibly defined and specified, and the later registration is also flexible to pick a specific level or a set of allowed levels with conflicts checked (such as two semantics in two levels from the level set selected of the same operation).
  - Context: User corrected the semantic-level design while the e-graph semantic-level correction was being applied.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_passes.md
  - Agent interpretation: Semantic levels are extensible typed keys, not a fixed enum; registry/pipeline selection may request one level or a typed set of allowed levels, with conflict detection when multiple selected definitions apply to the same owner without composition.

- 2026-04-23 12:52 local - Remove Fjfj semantics section and clarify DB deletion
  > There's no need to keep fjfj sections in compiler_semantics . What I think might be missed is the "deletion" operations of the DB. Or do you think it is not necessary to have deletion?
  - Context: User asked to remove Fjfj discussion from the semantics design and consider whether TraceDB needs deletion operations.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Remove Fjfj comparison from compiler_semantics.md and add a TraceDB deletion/retraction design. Prefer logical retraction/supersession over normal physical deletion so evidence and replay remain available.

- 2026-04-23 13:00 local - Clarify control-operation semantics
  > The semantics are generally in good shape. But how we program semantics of a control operation, such as scf.while or scf.for_each? Are they special?
  - Context: User asked whether control-flow operations need special semantic machinery after the operation-owned SemanticDef design.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: .repositories/xdsl/xdsl/interpreters/scf.py
  - Agent interpretation: Clarify that control operations are not globally special; their operation-owned semantic definitions orchestrate region execution, loop-carried facts, joins/fixpoints, and termination/fuel evidence through TraceDB.

- 2026-04-23 13:48 local - Resolve compiler semantics open questions
  > Let's solve Open Design Questions in the compiler_semantics.
  - Context: User asked to turn the remaining open questions in the active compiler semantics design into concrete design decisions.
  - Related: docs/in_progress/design/compiler_semantics.md
  - Related: docs/in_progress/design/compiler_passes.md
  - Agent interpretation: Replace the compiler semantics open-question list with resolved decisions for TraceDB schema, semantic registry composition, interpreter scope, control-region runner API, retention/compaction policy, and minimal eqsat operations.

- 2026-04-23 14:38 local - Clarify LLM-agent compiler action participation
  > Let's make it clear about how llm-agent might participate in the compiler passes. Generally, there are three types of actions: Fixed, AgentEvolve, AgentAct. Fixed means the ones that have programmed behavior, like passes/analysis/rewrites in MLIR/xDSL. AgentEvolve indicates that LLM agents evolve one fixed action to fill. And AgentAct indicates that the action itself is controlled or conducted by LLM agents directly. For CompilerAction, I think we should make it clear: 1. how to represent a match; 2. we should not model the mutation during apply. Instead, we can have a seperate Mutator stage to apply recorded mutations in the TraceDB. Such stages can be attached to the ending of CompilerAction, so a compiler action is generally match + apply + [optional stages]. If some records that must be handle (like mutation) remained in a TraceDB, the action failed. Also, required_facts/produced_facts should be absorted into match and apply. The design that using semantic execution in the pipeline is good, but we need it to be more clear: how many TraceDB will we have in a pipeline? How we handle or manage them?
  - Context: User refined the compiler pass/action design to distinguish fixed and LLM-driven actions, represent matches explicitly, move mutation into separate stages over TraceDB records, absorb required/produced facts into match/apply, and clarify TraceDB lifecycle in pipelines.
  - Related: docs/in_progress/design/compiler_passes.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/in_progress/design/compiler_semantics.md
  - Agent interpretation: Update compiler_passes.md around action kinds, MatchRecord, action stages including Mutator, pending-record failure rules, and pipeline TraceDB management.

- 2026-04-23 15:52 local - Correct AgentEvolve and AgentAct pass design
  > For AgentEvolve and AgentAct, intellic should provide more details. Current definitation of them to be specific Action of match, apply, and stages are wrong. Indeed, an AgentEvolve must do a JIT-like evolution to generate a Fixed action, so the AgentEvolve itself is not an action. On the other hand, AgentAct itself is an action, but we need to provide hooks or APIs for Agents to call and interatct with the compiler infra, not just an action of kind of fixed behavior.
  - Context: User corrected the compiler pass/action design after reviewing the Fixed/AgentEvolve/AgentAct model.
  - Related: docs/in_progress/design/compiler_passes.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Revise the pass design so AgentEvolve is a JIT-like evolution workflow that produces verified Fixed actions rather than a CompilerAction kind, while AgentAct remains a CompilerAction with explicit agent-facing compiler APIs/hooks.

- 2026-04-23 23:11 local - Resolve remaining compiler pass open questions
  > solve the open questions.
  - Context: User asked to resolve the remaining open questions in the compiler pass design while preparing the design set for merge review.
  - Related: docs/in_progress/design/compiler_passes.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Replace the remaining open-question block in compiler_passes.md with concrete decisions for TraceDB action indexing and cross-language Python/C++ action and evidence sharing, then propagate those decisions to the umbrella and source-note docs.

- 2026-04-23 23:28 local - Distinguish pipeline and action-owned TraceDBs
  > We may distinguish the pipeline logic TraceDB with other TraceDB's created, maintained, and used by specific Action to provide information. BOth should be supported. The pipeline logic TraceDB might be similar to the analysis-cache system?
  - Context: User refined the compiler pass design after the previous resolution of pass-design open questions.
  - Related: docs/in_progress/design/compiler_passes.md
  - Related: docs/in_progress/design/compiler_framework.md
  - Related: docs/notes/compiler_framework_sources.md
  - Agent interpretation: Support both an authoritative pipeline TraceDB and optional action-owned auxiliary TraceDB instances. Clarify that the pipeline TraceDB plays some cross-action roles similar to an analysis-cache system, but remains broader and evidence-bearing; auxiliary action TraceDBs may provide local cached or derived information and must export selected results into the pipeline TraceDB to affect pipeline behavior.

- 2026-04-24 00:57 local - Promote compiler architecture draft to accepted design
  > We should accept the draft to become an accepted-architecture design. Do the promotion.
  - Context: User decided to promote the compiler architecture draft into accepted design status after opening the draft PR.
  - Related: docs/design/compiler_framework.md
  - Related: docs/design/compiler_syntax.md
  - Related: docs/design/compiler_semantics.md
  - Related: docs/design/compiler_passes.md
  - Related: docs/todo/README.md
  - Agent interpretation: Promote the accepted architecture by moving the compiler design docs from docs/in_progress/design into docs/design, removing draft-only status language, updating task/todo/in-progress indexes, and aligning the PR metadata with accepted-architecture wording.
