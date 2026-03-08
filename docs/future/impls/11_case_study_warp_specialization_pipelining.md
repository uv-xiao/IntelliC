# Impl Case Study: Warp Specialization + Software Pipelining (end-to-end)

## Why this case study exists

Two “real compiler” features stress retargetable extensibility more than almost anything else:

1) **Warp/subgroup specialization**: partition a fixed execution group into roles (e.g., producer vs consumer), introduce
   role-local control flow, and define explicit handoff protocols across roles.
2) **Loop software pipelining**: overlap memory movement and compute by re-timing operations across iterations, inserting
   buffering, and discharging async/barrier effects into target-specific primitives.

This document shows a concrete HTP pipeline where each pass has two observable effect kinds:

- **AST mutation**: produces a new runnable Python stage program.
- **Analysis production**: emits a typed, serialized data structure staged under `ir/stages/<id>/analysis/`.

It also demonstrates why HTP insists on explicit contracts: without named analyses, typed effects, and capability gates,
these features quickly devolve into “target-specific pass soups”.

Design constraint used throughout:

- every stage remains runnable in `mode="sim"` (possibly stubbed with explicit diagnostics), so that debugging and
  minimization never depend on internal compiler state.

---

## 0) The input program (user code)

We use a simplified tiled GEMM inner loop to keep the example focused on the two features.

### 0.1 Kernel: “prefetch + compute” structure (portable intent)

```python
from htp import kernel, Tile, In, Out, f16, f32
from htp.intrinsics import portable as I

BM, BN, BK = 128, 128, 32

@kernel
def matmul_tile(A: In[Tile[BM, BK, f16]],
                B: In[Tile[BK, BN, f16]],
                C: Out[Tile[BM, BN, f16]]):
    acc: Tile[BM, BN, f32] = I.zeros((BM, BN), f32)

    # Two logical stages per k-iteration:
    #  - stage P: prefetch next A/B tiles
    #  - stage C: compute on the current tiles
    for k in range(0, K, BK):
        a = I.async_copy(A, k=k, scope="group_shared")
        b = I.async_copy(B, k=k, scope="group_shared")

        I.await_(a); I.await_(b)
        acc = I.mma(acc, I.load(a), I.load(b))

    C[:] = I.cast(acc, f16)
```

Notes:

- The kernel expresses *intent*: “these copies are async; this await defines a dependence”.
- It is not yet specialized to any particular subgroup (warp/wavefront) layout or any specific async primitive.
- `I.async_copy` and `I.await_` are **typed effects**; legality depends on the target `ArchModel`.

### 0.2 Schedule: request warp specialization and pipelining (constraints, not rewriting)

```python
from htp import schedule

@schedule(matmul_tile)
def matmul_sched(s):
    s.map(group="block", subgroup="warp")                 # declare the execution hierarchy
    s.warp_specialize(producers=2, consumers=6)           # roles within a block
    s.pipeline(loop="k", stages=3, buffer="pingpong")     # overlap P and C across iterations
```

Notes:

- The schedule does not “manually rewrite the kernel”. It declares constraints:
  - a role partition policy (`warp_specialize`)
  - a retiming/buffering policy (`pipeline`)
- The compiler must prove these constraints are satisfiable on the target and must explain failures with contract-level
  diagnostics.

---

## 1) Contracts we rely on (minimum)

This example relies on three contracted subsystems:

1) **Pass effects**: transform vs analysis is explicit (`docs/design/impls/02_pass_manager.md`).
2) **Typed effects**: async copy/await and barrier obligations must be represented and discharged, not implied by order.
3) **ArchModel capabilities**: the target declares which async primitives and subgroup partitions are available.

---

## 2) The pipeline (passes, effects, and staged artifacts)

Below is a concrete pipeline sketch. The exact names are illustrative; what matters is the structure and contracts.

### 2.1 Stage-by-stage overview

| Stage | Pass | Kind | AST effect | Key outputs |
|---|---|---|---|---|
| s00 | capture | transform | mutates | canonical entrypoints captured |
| s01 | ast_canonicalize@1 | transform | mutates | normalized loops/calls |
| s02 | typecheck_layout_effects@1 | mixed | mutates | typed `async_copy/await` effects |
| s03 | plan_warp_specialization@1 | analysis | preserves | `analysis/warp_role_plan.json` |
| s04 | apply_warp_specialization@1 | transform | mutates | role regions + handoff effects |
| s05 | analyze_loop_deps@1 | analysis | preserves | `analysis/pipeline_dependences.json` |
| s06 | plan_software_pipeline@1 | analysis | preserves | `analysis/pipeline_plan.json` |
| s07 | apply_software_pipeline@1 | transform | mutates | ping-pong buffers + retimed awaits |
| s08 | discharge_async_effects@1 | transform | mutates | target-neutral async protocol → target-required protocol |
| s09 | lower_<backend>@1 | transform | mutates | backend-ready form (may become `RunnablePyStubbed`) |
| s10 | emit_<backend>_package@1 | mixed | preserves | `codegen/<backend>/...` |

### 2.2 What the analysis artifacts look like (sketch)

All analyses are staged and indexed:

```
ir/stages/s03/analysis/
  index.json
  warp_role_plan.json
```

Example (sketch) `warp_role_plan.json`:

```json
{
  "schema": "htp.analysis.warp_role_plan.v1",
  "anchors": {
    "loop_entity_id": "module::matmul_tile:E12",
    "prefetch_call_entities": ["module::matmul_tile:E21", "module::matmul_tile:E22"],
    "mma_call_entities": ["module::matmul_tile:E40"]
  },
  "subgroup_kind": "warp",
  "roles": [
    {"name": "producer", "count": 2, "responsibilities": ["async_copy(A)", "async_copy(B)"]},
    {"name": "consumer", "count": 6, "responsibilities": ["mma", "accumulate"]}
  ],
  "handoffs": [
    {"from": "producer", "to": "consumer", "buffer": "group_shared", "protocol": "barriered_pingpong"}
  ],
  "constraints": {
    "requires": ["Arch.Subgroup", "Arch.Barrier", "Arch.AsyncCopy(group_shared)"]
  }
}
```

Similarly, pipelining plans are explicit and versioned:

```
ir/stages/s06/analysis/
  index.json
  pipeline_plan.json
```

`pipeline_plan.json` includes:

- stage count, prologue/steady/epilogue structure,
- which ops are moved across iteration boundaries,
- buffer allocation plan (ping-pong / ring),
- effect protocol plan (which `await`s become `wait_group`, etc.).

Design note: analyses that will be consumed by later transforms should use stable identities:

- statements/constructs by `entity_id`
- variables by `binding_id`

See identity model: `docs/design/impls/01_ir_model.md`.

---

## 3) The two big transforms (what they rewrite, concretely)

### 3.1 Warp specialization transform (s04)

Input intent:

- “prefetch A/B for each k iteration”
- “compute on A/B after await”

Transform objective:

- move prefetch responsibility to dedicated producer subgroups,
- define a *typed handoff protocol* to consumers,
- keep the stage runnable in `mode="sim"` using portable runtime shims.

Conceptual rewrite (sketch):

```python
role = I.subgroup_role()  # produced by specialization lowering

if role == "producer":
    for k in range(0, K, BK):
        a_tok = I.async_copy(A, k=k, scope="group_shared", slot=I.pingpong_slot(k))
        b_tok = I.async_copy(B, k=k, scope="group_shared", slot=I.pingpong_slot(k))
        I.signal_handoff(slot=I.pingpong_slot(k), toks=[a_tok, b_tok])

else:  # consumers
    for k in range(0, K, BK):
        I.wait_handoff(slot=I.pingpong_slot(k))
        acc = I.mma(acc, I.load_shared("A", slot=I.pingpong_slot(k)),
                         I.load_shared("B", slot=I.pingpong_slot(k)))
```

Key point: the handoff is not “just barriers sprinkled in”. It is a **typed effect protocol** that must be discharged by
later passes into the target’s concrete primitives (e.g., barrier + mbarrier tokens, fence scopes, etc.).

### 3.2 Software pipelining transform (s07)

Input after specialization:

- producer role emits `async_copy` and `signal_handoff`
- consumer role waits and computes

Transform objective:

- retime the loop so iteration `k+1` prefetch overlaps with iteration `k` compute,
- allocate ping-pong buffers and make dependence edges explicit.

Conceptual rewrite for consumers (sketch):

```python
I.wait_handoff(slot=0)                    # prologue
acc = I.mma(acc, I.load_shared("A", 0), I.load_shared("B", 0))

for k in range(1, K // BK):               # steady state
    I.wait_handoff(slot=k % 2)
    acc = I.mma(acc, I.load_shared("A", k % 2), I.load_shared("B", k % 2))

# epilogue omitted
```

Producer side is similarly retimed and may be expanded into “issue copies early, then signal later” depending on the
target’s async primitive semantics.

The important architectural claim:
> The pipeline transform is driven by staged analyses (`pipeline_dependences`, `pipeline_plan`), not by ad-hoc pattern
> matching inside a backend compiler.

---

## 4) Retargetability pressure points (and how HTP contains them)

Warp specialization and pipelining are hard to retarget because targets differ on:

- subgroup size and scheduling (warp vs wavefront vs “no fixed subgroup”),
- availability and semantics of async copies (token model, ordering, scopes),
- barrier primitives and memory model (who can wait, what is ordered, what is scoped),
- shared memory banking/layout constraints (a legality dimension that feeds back into the plan).

HTP contains this complexity by splitting the work into three layers:

1) **Target-neutral intent and protocols** (portable intrinsics + typed effects).
2) **Target-neutral planning** (staged analyses that depend on `ArchModel` capability declarations).
3) **Target-specific discharge/expansion** (small, capability-gated passes that map protocols to primitives).

The backend does not “own the feature”. The feature is a contracted pipeline slice that can be shared across backends.

---

## 5) What to look for in artifacts when debugging (practical)

If something goes wrong (wrong answers, deadlock, perf cliff), the artifact package is the debugging substrate:

- `ir/pass_trace.jsonl`: which pass introduced the protocol/retiming and which analyses justified it.
- `ir/stages/s03/analysis/warp_role_plan.json`: role partition and handoffs.
- `ir/stages/s06/analysis/pipeline_plan.json`: the schedule that was applied (or failed to apply).
- `ir/stages/s07/program.py`: runnable replay of the rewritten program (in `mode="sim"`, possibly stubbed).

This is the minimal set needed for long-term healthy development and for autonomous agent loops.
