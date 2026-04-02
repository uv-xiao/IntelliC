# IR Review and Native Surface Upgrades

- ID: `029-ir-review-native-surfaces`
- Branch: `htp/feat-ir-review-native-surfaces`
- PR: `https://github.com/uv-xiao/htp/pull/68`
- Status: `planned`
- Owner: `Codex`

## Goal

Start the next product-gap PR from a systematic IR infrastructure review, then
use that review to drive concrete IR refinement, WSP/CSP surface redesign, and
flagship example upgrades. The target is not only better docs; it is to remove
the IR barriers that still force metadata-shaped authoring and keep staged
programs from reading like native Python.

## Why

- contract gap: the AST-all-the-way redesign landed, but the current WSP/CSP
  stack still contains IR structures that push users toward builder ceremony and
  metadata choreography
- user-facing impact: flagship examples such as
  `examples/ast_frontend_composability/demo.py` still do not meet the
  human-friendly bar stated in `docs/story.md`
- architectural reason: the remaining product gap is now a joint problem across
  IR infrastructure, public surfaces, and example proof quality

## Scope Checklist

- [ ] review the current IR infrastructure and write
      `docs/design/ir_infrastructure_review.md`
- [ ] identify the specific IR structures in the WSP/CSP/core/program frontend
      stack that force metadata-shaped authoring and staged artifacts
- [ ] refine the typed IR so stage-local and process-local structure are more
      directly representable
- [ ] rebuild WSP/CSP authoring on that refined IR
- [ ] rewrite `examples/ast_frontend_composability/demo.py` and flagship
      WSP/CSP examples against the refined surfaces
- [ ] validate authored-surface readability, staged-artifact readability, and
      interpreter preservation with focused tests

## Code Surfaces

- producer: `htp/ir/core/`, `htp/ir/program/`, `htp/ir/frontends/`,
  `htp/ir/dialects/wsp/`, `htp/ir/dialects/csp/`, `htp/wsp/`, `htp/csp/`,
  `examples/`
- validator/binding: pass/interpreter surfaces as needed for runnable staged
  artifacts
- tests: `tests/ir/`, `tests/test_public_surfaces.py`, `tests/examples/`
- docs: `docs/design/`, `docs/todo/`, `docs/in_progress/`

## Test and Verification Plan

Required:
- [ ] one happy-path test
- [ ] one malformed-input / contract-violation test
- [ ] one regression test for the motivating gap
- [ ] human-friendly example updated or added
- [ ] `pixi run verify` or documented fallback

Do not add low-signal tests. Each added test must defend a concrete contract,
failure mode, or regression.

## Documentation Plan

- [ ] add `docs/design/ir_infrastructure_review.md`
- [ ] update `docs/design/` for implemented behavior after the fixes land
- [ ] update `docs/todo/` to remove or narrow the gap
- [ ] remove this file from `docs/in_progress/` before merge

## Commit Plan

1. create task file and clear stale prior task file
2. land IR review document
3. land IR refinement
4. land surface and example rewrites
5. sync docs, verify, review, and merge

## Review Notes

Reviewers should check that the PR does not stop at documentation. The review
document must translate into concrete IR fixes, cleaner public surfaces, and
better examples that actually raise the human-friendly bar.
