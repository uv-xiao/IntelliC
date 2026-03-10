# Programming Surface Conciseness Review

- ID: `026-programming-surface-conciseness-review`
- Branch: `htp/feat-programming-surface-conciseness-review`
- PR: `#61`
- Status: `in_progress`
- Owner: `Codex`

## Goal

Produce a critical PL/compiler-oriented review of HTP's current programming surfaces, with emphasis on human conciseness, semantic directness, and extension health. The output of this branch is not a surface implementation; it is a concrete review that turns syntax and ergonomics problems into follow-up feature tasks.

## Why

- contract gap: `docs/design/programming_surfaces.md` describes the current surface, but the repository still lacks a rigorous critique of where the syntax remains too indirect or semantically weak
- user-facing impact: if flagship examples still read like staged builder choreography instead of natural programs, HTP will fail its human-first claim even if the compiler substrate works
- architectural reason: frontend surface debt should be converted into explicit follow-up tasks before more syntax accretes on the wrong abstraction boundary

## Scope Checklist

- [x] compare current HTP kernel / WSP / CSP authoring against `references/pypto/`, `references/triton-distributed-knowingnothing/python/little_kernel/`, and current `examples/`
- [x] identify concrete conciseness and semantic-directness failures with critical commentary
- [x] convert those criticisms into explicit follow-up tasks under `docs/in_progress/` / `docs/todo/` as appropriate

## Review Findings

### 1. Kernel expressions improved, but kernel *control* is still not first-class enough

HTP has improved expression authoring (`store(C, A @ B)`, implicit temporaries, literal-bearing arithmetic), but non-trivial kernels still become explicit choreography around helper calls. Compared with LittleKernel's `ll.empty(...)`, `ll.unroll(...)`, and hardware intrinsics operating on locally declared values, HTP still makes the user repeat too much incidental detail:

- repeated `dtype="f32"` on staging and compute calls
- repeated source tensors inside each `async_copy(...)`
- no first-class tile/view slicing surface, so stage-local values are still whole-buffer placeholders instead of explicit views over indexed tiles
- loop variables do not yet participate as semantic index objects; they are only annotations on emitted ops

This means the current surface is *expression-first* but not yet *mainloop-first*.

### 2. WSP task authoring is still builder choreography, not a readable workload language

`htp.wsp` currently exposes a fluent builder, but flagship examples still read like repeated task metadata setup:

- `.tile(...)`, `.bind(...)`, `.pipeline(...)`, `.resources(...)` repeated on every task
- `.role(...)`, `.prologue(...)`, `.steady(...)`, `.epilogue(...)` encode narrative as string tags instead of executable task bodies
- the same kernel is launched three times to narrate load/mainloop/store phases, rather than expressing one coherent workload with role-local code blocks

This is a design smell. The schedule is real, but the authored program still reads like a serialization scaffold rather than a workload language.

### 3. CSP remains the weakest surface semantically

`htp.csp` still relies on `.compute("name", ...)` markers. That is not a process language; it is task metadata with embedded comments. The surface does not yet let users write protocol-local code in normal Python. As a result:

- process steps are names, not executable bodies
- channels participate in the compiler, but process-local transformations do not
- the flagship CSP example proves protocol tracing more than it proves a convincing user surface

For a framework claiming AST-centric programming, this is a real gap.

### 4. Kernel/workload coupling still leaks stringly-typed plumbing

Across WSP and CSP, task/process builders still pass argument names as strings:

- `args=("A", "B", "C", "M", "N", "K")`
- channel references become strings quickly after construction

That keeps the payload stable, but it weakens authoring integrity. The user is still partially writing the serialized interface rather than writing one coherent Python program whose bindings are inferred from values and scopes.

### 5. Examples are better than before, but still below the reference bar

The HTP examples are now less toy-like, but they still lag the references in semantic fullness:

- the WSP GEMM examples narrate stages, but they do not express realistic tile coordinates, stage advancement, or ownership transitions at the same semantic resolution as the LittleKernel GEMM reference
- the CSP example has better role names, but still does not present a convincing end-to-end protocol program
- PyPTO examples show stronger function/routine decomposition than HTP's current high-level surfaces

The result is that HTP's syntax is improving, but its examples still do not fully prove the surface quality claim.

## Derived Follow-Up Tasks

These should become the next programming-surface PRs, in order.

1. **Tile/view and loop-index surface**
   - first-class tile/view slicing on native kernel values
   - semantic loop indices that feed views and staged memory ops
   - goal: kernels should express `A_tile`, `B_tile`, and stage-local movement as real program values, not whole-buffer placeholders

2. **WSP scoped schedule defaults and task bodies**
   - remove repeated per-task schedule boilerplate by introducing inherited/default schedule context
   - replace string stage markers with real task-local authored bodies or structured step blocks
   - goal: WSP examples should read like one workload program, not repeated builder setup

3. **CSP process-body surface**
   - process authoring should support executable local bodies around `get(...)`, `put(...)`, and compute steps
   - remove `.compute("name", ...)` as the flagship style
   - goal: CSP should become a true authored process language

4. **Argument/channel binding by value, not string tuples**
   - infer task/process argument wiring from kernel/routine values or named bind objects
   - keep payload strings as an emitted representation, not the authored surface

5. **Reference-grade flagship example rewrite**
   - rebuild WSP/CSP examples against `references/pypto/`, `references/triton-distributed-knowingnothing/python/little_kernel/`, and `references/arknife/`
   - make them semantically meaningful enough to serve as readability and regression anchors

## Code Surfaces

- producer: `htp/kernel.py`, `htp/wsp/`, `htp/csp/`, `examples/`
- validator/binding: none for this review task
- tests: docs/policy verification only
- docs: `docs/design/programming_surfaces.md`, `docs/design/littlekernel_ast_comparison.md`, `docs/todo/programming_surfaces.md`, `docs/in_progress/README.md`

## Test and Verification Plan

Required:
- [x] one happy-path test
- [x] one malformed-input / contract-violation test
- [x] one regression test for the motivating bug or gap
- [x] human-friendly example updated or added
- [x] `pixi run verify` or documented fallback

This is a review/documentation task. Instead of feature tests, the verification surface is:

- PR policy / docs consistency checks
- the explicit conversion of surface criticism into tracked follow-up tasks

## Documentation Plan

- [ ] update `docs/design/` if the review sharpens the implemented story
- [x] update `docs/todo/` with precise follow-up tasks
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file
2. perform reference-backed review
3. translate findings into TODO / follow-up tasks
4. sync design and in-progress docs
5. rebase, review, and merge

## Review Notes

Reviewers should check whether the criticism is technically grounded in the code and references rather than aesthetic preference, and whether the resulting follow-up tasks are large enough to drive real PRs.

## Verification Evidence

- local fallback verification used because this branch only changed docs/policy-facing files
- `pytest -q tests/test_docs_layout.py tests/test_pr_policy_script.py`
- `pre-commit run --all-files`
