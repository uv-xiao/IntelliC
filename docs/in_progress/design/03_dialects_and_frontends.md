# Dialects and Frontends

## Uniform dialect model

Builtin and extension features are both dialects.

They use the same substrate for:

- nodes
- aspects
- analyses
- intrinsics
- frontends
- interpreters
- passes
- lowering hooks

The difference is repository ownership and packaging, not semantic mechanism.

## Relationship to existing systems

HTP should learn from PyPTO, Arknife, Allo, and LittleKernel without importing
their private IRs as semantic owners.

HTP core may absorb only generic abstractions that recur across systems.
System-specific constructs remain adapters or dialect-owned features.

## IR-definition substrate

The preferred IR-definition substrate is a Python EDSL:

- ordinary Python classes
- decorators for registration/schema attachment
- Python AST for inspection/normalization

Not acceptable:

- heavy hidden metaclass magic
- per-frontend ad hoc mini-compilers
- AST-walking execution semantics

## Frontend-definition mechanism

The substrate should provide an optional frontend-definition mechanism for each
dialect.

A dialect may use:

- explicit core construction only
- the substrate frontend mechanism
- or both

The frontend mechanism should support:

- decorator or capture entry definition
- AST matching helpers
- composable rule objects
- typed IR construction callbacks
- provenance attachment
- centralized error handling

This is effectively an object-oriented parser-combinator API for authoring
sugar and JIT capture.

## Implemented status (frontend-definition substrate)

The initial frontend-definition substrate is now implemented in code:

- a rule-backed frontend-definition substrate now exists in `htp/ir/frontend_rules.py`
  (`FrontendBuildContext`, `FrontendRule`, `FrontendRuleResult`,
  `ProgramSurfaceRule`)
- builtin public surfaces are resolved through registered `FrontendSpec` objects
  in `htp/ir/frontends.py` (`resolve_frontend(...)`, `FrontendSpec.build(...)`)
- builtin `htp.kernel`, `htp.routine`, `htp.wsp`, and `htp.csp` public
  surfaces now all use `rule=`-backed `FrontendSpec` registration rather than
  direct `build_program_module=` callbacks
- `to_program_module()` on routine/WSP/CSP now delegates back through the
  registered frontend rule instead of owning a parallel lowering body

Remaining gap relative to this design document:

- the current rules still rebuild workload/process structure from payload-shaped
  surface fields; the final node-first rule/combinator API described above is
  not implemented yet

Code pointers for the implemented substrate:

- `htp/ir/frontend_rules.py`
- `htp/ir/frontends.py`
- `htp/ir/frontend.py`
- `htp/kernel.py`
- `htp/compiler.py`

## Intrinsic model

Intrinsics are also dialect-owned registry objects.

They should not be implemented as one hard-coded switchboard.

Each intrinsic definition should declare:

- `intrinsic_id`
- owning dialect
- argument/result schemas
- purity/effect metadata
- typing rules
- interpreter hook
- renderer rule
- lowering hooks
- legality constraints

Committed stages may contain only intrinsics that:

- have an interpreter path
- or are explicitly replay-stubbed through structured diagnostics

## Dialect packaging and discovery

Each dialect should declare a manifest-like contract with:

- `dialect_id`
- `version`
- `kind`
- exported nodes/aspects/analyses/intrinsics/frontends/interpreters/passes
- dependencies

HTP should activate an explicit dialect set per compile/run session.

It must not rely on import-order side effects.
