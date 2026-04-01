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

## Frontend composability rules

Dialect frontend features must compose through the same substrate.

Every new capture feature must be reviewable against these checks:

- parse/capture: it coexists with other active dialect handlers in one module
- typed IR: it lowers into the shared `ProgramModule` instead of creating a
  private semantic owner
- passes: pass logic sees one typed IR/aspect space rather than parallel
  payloads
- execution: interpreter dispatch composes through the shared object-oriented
  interpreter substrate
- artifacts: the composed result still renders to one normalized Python module

Cross-dialect cooperation is allowed only through explicit typed interfaces.
Dialects must not couple themselves through ad hoc payload conventions or by
depending on another dialect's private helper layout.

Frontend AST handlers must stay small and single-purpose. One handler should
recognize one local syntax form and lower one local construct.

## Implemented status (frontend-definition substrate)

The frontend-definition substrate is now implemented in code:

- a rule-backed frontend-definition substrate now exists in `htp/ir/frontends/rules.py`
  (`FrontendBuildContext`, `FrontendRule`, `FrontendRuleResult`,
  `ProgramSurfaceRule`)
- a shared AST capture substrate now exists in:
  - `htp/ir/frontends/ast_context.py`
  - `htp/ir/frontends/ast_handlers.py`
  - `htp/ir/frontends/ast_visitor.py`
- builtin public surfaces are resolved through registered `FrontendSpec` objects
  in `htp/ir/frontends/__init__.py` (`resolve_frontend(...)`, `FrontendSpec.build(...)`)
- builtin `htp.kernel`, `htp.routine`, `htp.wsp`, and `htp.csp` public
  surfaces now all use `rule=`-backed `FrontendSpec` registration rather than
  direct `build_program_module=` callbacks
- `to_program_module()` on routine/WSP/CSP now delegates back through the
  registered frontend rule instead of owning a parallel lowering body
- WSP and CSP public specs now expose typed top-level surface objects rather
  than raw dict payload fields before serialization
- WSP and CSP now also support AST-backed nested-function authoring through:
  - nested `@w.task(...)` / `@w.mainloop(...)` local functions with local
    `w.step(...)` bodies
  - nested `@c.process(...)` local functions with local `c.get(...)`,
    `c.put(...)`, `c.compute(...)`, and `c.compute_step(...)` bodies
- AST-backed WSP/CSP modules now record `meta["frontend_capture"] == "ast"`

Remaining gap relative to this design document is now narrower:

- richer typed schedule/stage/process local state still needs to migrate out of
  generic attr payloads in some emitted task/process records
- broader dialect/extension migration onto this frontend substrate is still open

Code pointers for the implemented substrate:

- `htp/ir/frontends/rules.py`
- `htp/ir/frontends/__init__.py`
- `htp/ir/frontends/ast_context.py`
- `htp/ir/frontends/ast_handlers.py`
- `htp/ir/frontends/ast_visitor.py`
- `htp/ir/dialects/wsp/frontends.py`
- `htp/ir/dialects/csp/frontends.py`
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
