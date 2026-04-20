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
