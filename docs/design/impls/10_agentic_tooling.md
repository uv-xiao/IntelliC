# Impl: Built-in Agent Loop for Compiler Development (Fully Autonomous)

## Goal

Define an HTP-provided agent loop that can autonomously:

- triage failures and regressions,
- propose compiler changes (bounded to safe corridors),
- verify the changes,
- and record full provenance in emitted artifacts.

This is a *developer tool* for compiler evolution, not part of end-user compilation in production by default.

## Core idea: agents consume and produce artifact packages

The unit of interaction is the **artifact package**:

- input: a package that reproduces a bug/regression (or a workload + pinned pipeline)
- output: a package that includes:
  - the applied patch (or a structured change description),
  - verification results,
  - updated manifests/traces,
  - and a promotion recommendation.

This avoids “agent memory drift” and ensures changes are replayable.

In HTP, replayability includes not only transformed IR snapshots, but also the **analyses that justified transforms**:

- each stage may contain `ir/stages/<id>/analysis/` results (versioned, schema-tagged)
- `ir/pass_trace.jsonl` records whether a pass mutated the AST and which analyses it produced/consumed

This is critical for long-term autonomy: the agent must reason from evidence, not from implicit invariants.

## Agent architecture (recommended)

### 1) State machine

1. **Observe**
   - load artifact package
   - read manifest + pass trace + diagnostics
   - load relevant stage analyses (`ir/stages/<id>/analysis/index.json`)
2. **Localize**
   - map failure to a contract boundary (capability/effect/layout/backend handler)
   - minimize to the smallest reproducer if needed
3. **Plan**
   - enumerate candidate edits within safe corridors:
     - add/modify a pass
     - adjust pipeline parameters
     - add/modify an intrinsic handler behind capability gates
4. **Patch**
   - apply code change using templates (bounded surface area)
5. **Verify**
   - run type/effect checks first
   - run golden artifact tests
   - run target-specific correctness tests
   - run perf checks when configured
6. **Record**
   - write a structured “agent run report” into the artifact outputs:
     - what changed
     - why (evidence pointers)
     - what gates passed/failed
     - which analyses changed (semantic diffs of analysis outputs are often the earliest signal of regressions)
7. **Promote**
   - optionally open a PR / land the change depending on repo policy

### 2) Tool API the agent requires

HTP should expose a stable API/CLI surface for the agent:

- `htp compile --emit-package ...`
- `htp replay <package>`
- `htp diff --semantic <pkgA> <pkgB>` (capabilities/effects/layout deltas)
- `htp minimize <package>` (reduce to minimal failing input)
- `htp verify <package>` (standard gates)
- `htp explain <diagnostic>` (contract-oriented explanation)

The built-in agent loop is then a thin orchestrator over these tools.

## Safety model for “fully autonomous”

“Fully autonomous” does not mean “unbounded”. It means:

- **bounded edit surfaces** (templates + allowlists)
- **mandatory verification gates** before any promotion
- **structured provenance** for auditability

Recommended policies:

- allow edits only under known extension roots (e.g., `htp/` compiler code, `docs/`, registered plugin directories)
- forbid direct edits to generated outputs
- require all changes to pass:
  - contract/type/effect checks
  - golden artifact diffs
  - and target-specific correctness tests
- perf regressions must be either eliminated or explicitly acknowledged in the agent report

## Verification gates (non-negotiable, ordered)

Fully autonomous only works if verification is standardized and cheap-to-run early:

1) **Static contract checks**
   - capability satisfiability (pipeline solver must succeed)
   - layout legality checks
   - effect/protocol checks (channels, buffered handoffs, collectives)

2) **Golden artifact diffs**
   - compare `manifest.json` + selected IR dumps + selected codegen outputs
   - require “expected diffs only” (agent must justify changes via structured reasons)

3) **Targeted correctness**
   - run minimal unit tests for touched passes/intrinsics
   - run end-to-end compile+execute for a small representative suite per backend

4) **Performance (when configured)**
   - microbench gates for kernels affected by the change
   - regression threshold policy (absolute and relative)

The agent loop should treat any gate failure as a *localization signal* (what contract boundary is missing), not as a
generic “try again”.

## Agent policy and provenance schema (recommended)

To keep autonomy healthy over months/years, every run must leave structured evidence.

### 1) Policy input (example)

The agent loop should accept a policy file (e.g., `agent_policy.toml`) that defines:

- allowed edit roots (paths)
- required gates (which checks must pass)
- perf thresholds
- promotion mode (auto-land vs PR vs patch-only)

### 2) Provenance output (manifest extension)

The artifact manifest should record agent activity under an extension namespace, e.g.:

- `extensions.agent.run_id`
- `extensions.agent.goal` (bugfix / perf / retargeting / refactor)
- `extensions.agent.patch_summary` (structured: pass/pipeline/intrinsic/backend handler)
- `extensions.agent.evidence` (pointers to logs/dumps/diagnostics)
- `extensions.agent.gates` (pass/fail + timings)
- `extensions.agent.decision_trace` (search steps, candidates tried, why rejected)

This makes agent work auditable and makes future agents “inherit evidence” rather than repeating mistakes.

## Why the agent loop is healthier in HTP than in MLIR-first stacks

The loop depends on HTP’s design choices:

- pass/pipeline contracts are explicit (`requires/provides/invalidates`)
- capabilities/effects/layout are typed and dumpable
- artifacts are stable and replayable
- diagnostics localize to contract boundaries

In MLIR-first ecosystems, you *can* build similar tooling, but it is often layered on after the fact, and must reverse-
engineer the implicit invariants that live in pass ordering and dialect conventions.

### Comparative notes (Triton/JAX reality check)

- **Triton**: real “feature work” often spans Python pipeline wiring + multiple MLIR passes + target-specific dialect
  lowerings. An agent can succeed, but only if the system emits a minimal, structured explanation bundle (pipeline,
  contracts, invariants). HTP makes that the default contract, not an afterthought.
- **JAX/XLA**: the portable layer (StableHLO/HLO) is great for many graph-level transforms, but low-level kernel semantics
  tend to live behind backend emitters/custom calls/vendor libraries. Autonomous changes therefore frequently require
  touching large backend subsystems rather than small, typed extension units.

## Next doc links

- Capability typing: `docs/design/feats/01_extensibility.md`
- Pass tracing: `docs/design/impls/02_pass_manager.md`
- Manifest schema: `docs/design/impls/04_artifact_manifest.md`
- Debug requirements: `docs/design/feats/09_debuggability.md`
