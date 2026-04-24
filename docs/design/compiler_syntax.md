# Design: Compiler Syntax

> Status: Accepted architecture design for IntelliC syntax (`Sy`).

## Goal

Define `Sy`, the syntax half of IntelliC IR:

```text
IR := Sy + Se
```

`Sy` owns what programs look like: operations, regions, blocks, values, types,
attributes, dialects, structural verification, and canonical text. It must be
strong enough to host future compiler IRs while staying readable to humans and
LLM agents.

## Decision

Use the MLIR/xDSL syntax model and strictly match MLIR/xDSL textual format.
Because xDSL is already Python-native, IntelliC should copy selected xDSL classes
into native IntelliC and modify them to meet IntelliC's architecture requirements. IntelliC
should not wrap/import xDSL as the public compiler infrastructure.

This syntax design does not include xDSL's declarative operation-definition
machinery as a core concept. The first clean syntax contract should be the
MLIR/xDSL object and parser model: operations, regions, blocks, values, types,
attributes, dialect registration, parser, printer, and structural verifier.

## Reference Map

The syntax design intentionally borrows most of its shape from MLIR and xDSL.
These links point to the local reference checkouts used for this draft. They are
design evidence, not runtime dependencies: IntelliC should copy/adapt the useful
pieces behind native package names.

| Syntax Area | Reference Links | IntelliC Use |
| --- | --- | --- |
| MLIR syntax model | [MLIR LangRef](../../../.repositories/llvm-project/mlir/docs/LangRef.md) | Operations, values, blocks, regions, attributes, types, and canonical text model |
| xDSL IR object model | [xdsl/ir/core.py](../../../.repositories/xdsl/xdsl/ir/core.py) | `Dialect`, `Operation`, `Region`, `Block`, `SSAValue`, `OpResult`, `BlockArgument`, `Use`, `Attribute`, and type/attribute base classes |
| Context and dialect loading | [xdsl/context.py](../../../.repositories/xdsl/xdsl/context.py) | Dialect, operation, attribute, and type registration shape |
| Parser | [xdsl/parser/core.py](../../../.repositories/xdsl/xdsl/parser/core.py), [xdsl/utils/mlir_lexer.py](../../../.repositories/xdsl/xdsl/utils/mlir_lexer.py) | Strict MLIR-compatible IR parser, SSA/block reference handling, diagnostics |
| Printer | [xdsl/printer.py](../../../.repositories/xdsl/xdsl/printer.py) | SSA/block name allocation, generic/custom operation printing, round-trip text evidence |
| Builder and insertion | [xdsl/rewriter.py](../../../.repositories/xdsl/xdsl/rewriter.py), [xDSL builders notebook](../../../.repositories/xdsl/docs/marimo/builders.py) | Insertion points, operation insertion, parent/use-list mutation discipline |
| Introductory xDSL/MLIR docs | [xDSL MLIR IR notebook](../../../.repositories/xdsl/docs/marimo/mlir_ir.py), [xDSL introduction](../../../.repositories/xdsl/docs/marimo/xdsl_introduction.py) | Human-readable examples for `func`, `arith`, `scf`, textual IR, and dialect namespaces |
| Dialect definitions used in examples | [builtin.py](../../../.repositories/xdsl/xdsl/dialects/builtin.py), [func.py](../../../.repositories/xdsl/xdsl/dialects/func.py), [arith.py](../../../.repositories/xdsl/xdsl/dialects/arith.py), [cf.py](../../../.repositories/xdsl/xdsl/dialects/cf.py), [scf.py](../../../.repositories/xdsl/xdsl/dialects/scf.py), [affine.py](../../../.repositories/xdsl/xdsl/dialects/affine.py) | First-slice example dialects and operation constructors |
| MLIR SCF and Affine operation definitions | [SCFOps.td](../../../.repositories/llvm-project/mlir/include/mlir/Dialect/SCF/IR/SCFOps.td), [AffineOps.td](../../../.repositories/llvm-project/mlir/include/mlir/Dialect/Affine/IR/AffineOps.td), [Affine dialect doc](../../../.repositories/llvm-project/mlir/docs/Dialects/Affine.md) | Full SCF coverage beyond xDSL's current subset, affine maps/sets, affine operations, and verification rules |
| xDSL verification/test evidence | [test_ir.py](../../../.repositories/xdsl/tests/test_ir.py), [test_parser.py](../../../.repositories/xdsl/tests/test_parser.py), [test_printer.py](../../../.repositories/xdsl/tests/test_printer.py), [test_context.py](../../../.repositories/xdsl/tests/test_context.py) | Expected behavior examples for structure, parser, printer, and context tests |
| MLIR operation/dialect definition background | [MLIR ODS operations](../../../.repositories/llvm-project/mlir/docs/DefiningDialects/Operations.md), [MLIR dialect docs](../../../.repositories/llvm-project/mlir/docs/DefiningDialects/_index.md) | Background for later declarative operation-definition machinery; not required in the first syntax slice |

Reference rule: when this document says "copy/adapt xDSL," the primary source
is the linked xDSL class or module in this table. When xDSL behavior conflicts
with IntelliC's native API, construction evidence, or semantic-definition
contracts, IntelliC keeps the MLIR-compatible syntax shape but changes the API
behind its own package boundary.

## Surface Construction And Parser Boundary

IntelliC has one strict canonical parser family and one Python-native surface
construction layer:

```text
surface_api:
  modular Python construction APIs for human/LLM-facing authoring
  construct native Sy objects or canonical IR fragments directly
  share insertion context, diagnostics, symbol/type helpers, and evidence

ir_parser:
  canonical IR parser
  copied/adapted from xDSL's existing MLIR-compatible parser
  strictly follows MLIR/xDSL operation, region, block, type, and attribute syntax
```

The surface layer should not be a hardened Python parser and should not rely on
parser-level composition. Instead, dialects and operations expose high-level
Python builders, decorators, type constructors, operator hooks, and
region/context-manager helpers. These APIs construct `Sy` directly under a
controlled insertion context.

The IR parser must accept canonical IR text and reject noncanonical syntax. It
is used for reading canonical IR, round-trip evidence, and text interchange, not
for accepting Pythonic authoring forms.

## Syntax Model

Core objects copied/adapted from xDSL where useful:

```text
Context
  Dialect
    Operation classes
    Attribute classes
    Type classes

Operation
  name: fully qualified dialect operation name
  operands: tuple[Value, ...]
  results: tuple[OpResult, ...]
  properties: inherent operation data
  attributes: discardable or annotation data
  regions: tuple[Region, ...]
  successors: tuple[Block, ...]
  location: source/evidence location

Region
  blocks: ordered blocks

Block
  arguments: tuple[BlockArgument, ...]
  operations: ordered operations

Value
  type: Type
  owner: OpResult | BlockArgument
  uses: tracked use list

Use
  value: Value
  owner: Operation
  operand_index: int

Type / Attribute
  immutable compile-time objects

SourceLocation
  file | module | generated
  line/column when available
  evidence id when generated by a builder
```

This mirrors MLIR/xDSL because those projects already solved many structural
problems: SSA use lists, nested regions, block arguments, dialect namespaces,
custom assembly, generic operation syntax, and open type/attribute systems.

## Minimal Core API

The first implementation slice should expose a small explicit API before adding
ergonomic shortcuts:

```python
op = Operation.create(
    name="arith.addi",
    operands=(lhs, rhs),
    result_types=(i32,),
    properties={},
    attributes={},
    regions=(),
    successors=(),
    loc=loc,
)
```

Planned construction contracts:

- `Operation.create` builds a detached operation with result values and no block
  owner.
- `Builder.insert(op)` attaches a detached operation to the active block and
  updates parent links and use lists.
- `Region` owns an ordered block list. `Block` owns ordered operations and block
  arguments.
- Reparenting an attached operation requires an explicit mutation API; direct
  list mutation is not public.
- Replacing an operand updates both the operation operand tuple and the old/new
  value use lists.
- Values are identity objects, not names. Printed SSA names are assigned by the
  printer.
- Types and attributes are immutable value objects. Surface helpers may reuse
  singleton type objects such as `i32`.

Minimal planned package shape:

```text
intellic/ir/syntax/
  operation.py       # Operation, OpResult
  region.py          # Region, Block, BlockArgument
  value.py           # Value, Use
  type.py            # Type
  attribute.py       # Attribute
  builder.py         # Builder, InsertionPoint, mutation helpers
  location.py        # SourceLocation and construction evidence links
```

## Python Construction APIs

Pythonic authoring should feel close to native Python while staying explicit
about IR construction. The surface API composes normal Python mechanisms rather
than syntax parsers:

```text
Operation or dialect API
  builder functions: arith.addi(lhs, rhs), arith.constant(value, type)
  type constructors: i32, index, tensor[...]
  value hooks: Value.__add__ -> arith.addi when a typed construction policy provides it
  decorators: func.ir_function, builtin.module
  region helpers: insertion points and context managers for nested regions
```

A decorator can stage a Python function by creating symbolic block arguments,
running the function under an insertion context, converting the returned value
into terminator operations where appropriate, and then invoking structural
verification. Source evidence is based on builder/decorator calls and available
Python location metadata; exact AST node spans are optional evidence, not a core
parser contract.

Host Python control flow and symbolic IR control flow must stay distinct. A
symbolic `Value` cannot be consumed as a Python `bool`. IR control-flow
operations should be explicit builders or region helpers such as `scf.if_` or
`cf.br`.

### Builder And Insertion Context

`surface_api` construction runs through an explicit builder stack:

```python
with Builder() as builder:
    with builder.insert_at_end(block):
        c1 = arith.constant(1, i32)
        y = arith.addi(x, c1)
```

Contracts:

- Builder state is scoped. A builder function fails if no active insertion point
  exists, unless it is explicitly documented to return a detached operation.
- Dialect builders insert operations through the active builder instead of
  mutating blocks directly.
- Builders return the useful operation results by default. For multi-result or
  region-owning operations, builders may return a typed handle with both
  operation and result access.
- Every builder records construction evidence: builder name, dialect/op name,
  input values or attributes, emitted operation ids, active insertion point, and
  source location when available.
- After staging, structural verification runs over the produced module or
  function before semantic mechanisms run.

### Dialect-Owned Builders

Dialects expose Python construction APIs near the operations they own:

```python
c1 = arith.constant(1, i32)
y = arith.addi(x, c1)
func.return_(y)
```

Contracts:

- A dialect builder is a typed convenience wrapper around `Operation.create` and
  `Builder.insert`.
- Builder names should follow Python conventions when MLIR names collide with
  Python keywords, such as `func.return_`.
- Builders perform local shape checks that are cheap and syntax-owned, such as
  result count, region count, and required attribute presence.
- Cross-operation meaning belongs to semantic definitions or later verifier passes,
  not hidden builder state.

### Function Decorator Staging

`func.ir_function` is the first decorator surface:

```python
@func.ir_function
def sum_to_n(n: index) -> i32:
    zero_i = arith.constant(0, index)
    one_i = arith.constant(1, index)
    zero = arith.constant(0, i32)
    with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
        i, total = loop.arguments
        scf.yield_(arith.addi(total, arith.index_cast(i, i32)))
    return loop.results[0]
```

Staging contract:

1. Read the Python callable signature and type annotations.
2. Create a `func.func` operation with one entry block.
3. Create `BlockArgument` values for annotated parameters.
4. Execute the Python callable once with those symbolic values under an insertion
   context for the entry block.
5. Convert the returned `Value` or tuple of values into `func.return` unless the
   body already emitted an explicit terminator.
6. Attach construction evidence to the function and emitted operations.
7. Run structural verification and optionally run printer/parser round-trip
   evidence.

The decorator does not parse source code. Any host Python side effects in the
decorated function happen during staging, so examples and docs should keep
decorated functions side-effect-light and builder-focused.

### Operator Hooks

Operator hooks are optional construction-policy behavior over `Value`, not universal
syntax:

```python
x + 1       # active policy lowers to arith.addi(x, arith.constant(1, i32))
x > 0       # active policy lowers to a comparison operation
```

Contracts:

- `Value.__bool__` always fails with a diagnostic. Python `if`, `and`, `or`, and
  `not` must not silently construct IR.
- Numeric operator hooks consult the active construction policy. If no operation is
  registered for the operand types, the hook fails with a diagnostic.
- Python literals may be converted to constants only through active policy
  rules, so integer width and type inference stay explicit enough for evidence.
- Operator hooks are convenience APIs. Every hook must have an equivalent named
  builder such as `arith.addi`.

### Region Helpers

Region-owning operations use explicit context managers:

```python
with scf.if_(x > 0, result_types=(i32,)) as if_:
    with if_.then():
        scf.yield_(x)
    with if_.else_():
        scf.yield_(arith.neg(x))
result = if_.result
```

Contracts:

- Region helpers create the owning operation and its regions before entering
  nested insertion contexts.
- Each nested region context has a clear active block.
- Required terminators are checked structurally after construction.
- Region helpers return typed handles so callers can access operation results
  without relying on generated SSA names.

### Construction Evidence

Construction evidence is syntax-owned provenance, separate from semantic
database records:

```text
ConstructionEvidence
  event_id
  builder_name
  op_name
  source_location
  insertion_point
  inputs
  emitted_operation_ids
  diagnostics
```

This evidence should be enough for tests and agent review to explain how a
Python API call produced a specific operation. Later semantic execution and pass
database records may link to construction evidence, but they should not replace
it.

## Strict Text Format

The IR parser and printer should follow MLIR/xDSL syntax:

```text
operation             ::= op-result-list? (generic-operation | custom-operation)
generic-operation     ::= string-literal `(` value-use-list? `)` successor-list?
                          properties? region-list? dictionary-attribute?
                          `:` function-type location?
custom-operation      ::= bare-id custom-operation-format
op-result-list        ::= op-result (`,` op-result)* `=`
region-list           ::= `(` region (`,` region)* `)`
properties            ::= `<` dictionary-attribute `>`
```

IntelliC may choose a canonical generic form for early implementation, but that form
must still be MLIR/xDSL-compatible.

## Dialect Naming

IntelliC is not a dialect. Do not use infrastructure-name-prefixed placeholder
operations unless a future design creates a real dialect with that name.

Use existing MLIR-style dialect names in examples:

- `builtin.module`
- `func.func`
- `func.return`
- `arith.constant`
- `arith.addi`
- `cf.br`
- `scf.if`
- `scf.forall`
- `affine.apply`
- `affine.for`
- `affine.load`

If IntelliC later adds domain dialects, those dialects need their own design docs.

## Full SCF Syntax Coverage

`scf` is an implementation-ready dialect family, not just a source of loop
examples. The syntax layer must provide typed operation classes, parse/print
coverage, builders, region conventions, and structural verification for the full
MLIR SCF surface:

| Operation | Syntax contract |
| --- | --- |
| `scf.if` | condition is `i1`; result types require both regions; regions are single-block; yields match result types |
| `scf.for` | bounds/step share induction type; body block args are `(iv, iter_args...)`; yields match loop-carried values |
| `scf.while` | before/after regions; `scf.condition` terminates before region; after region yields next operands; result type matching follows the condition payload |
| `scf.execute_region` | region may contain multiple blocks; result types require `scf.yield`; optional no-inline-style attributes are preserved |
| `scf.index_switch` | index flag, case values, case/default regions, and multi-result yields |
| `scf.parallel` | lower/upper/step lists have equal rank; body block args are one index per dimension; optional reductions match results |
| `scf.reduce` | terminator for `scf.parallel`; one reduction region per operand; region block args model accumulator and element |
| `scf.reduce.return` | terminator for a reduce region; operand type matches reduce operand/result |
| `scf.yield` | terminator for `scf.if`, `scf.for`, `scf.while` after-region, `scf.execute_region`, and `scf.index_switch` regions |
| `scf.condition` | terminator for `scf.while` before-region; first operand is condition and remaining operands are payload/result candidates |
| `scf.forall` | multidimensional parallel loop with shared outputs, mapping attributes, body block args, and implicit synchronization |
| `scf.forall.in_parallel` | designated terminator for `scf.forall`; carries parallel combining/yielding operations for shared outputs |

The xDSL checkout currently covers many SCF operations but not every MLIR SCF
operation. IntelliC should copy/adapt xDSL where available and implement missing
MLIR SCF operations natively. The public contract is MLIR-compatible SCF, not
"whatever xDSL currently happens to expose."

## Affine Syntax Coverage

Affine is a core optimization dialect for IntelliC. Syntax must include both
the polyhedral data structures and the operation classes that use them:

| Syntax area | Contract |
| --- | --- |
| `AffineExpr` | immutable expression tree for constants, dims, symbols, add/sub/mul-by-constant, ceildiv/floordiv/mod by positive constants, and semi-affine extensions tracked explicitly |
| `AffineMap` | dimension/symbol counts, result expressions, named and inline printing, eval, compose, simplify, used-dim/symbol analysis |
| `AffineSet` | affine constraints over dims/symbols, integer-set parsing/printing, constraint evaluation |
| `affine.apply` | one-result map, map operand count equals dims plus symbols, result type is `index` |
| `affine.for` | lower/upper affine maps plus operands, positive integer step, induction variable, loop-carried values, region/yield verification |
| `affine.if` | affine set condition, then/else regions, yielded result type checks |
| `affine.parallel` | grouped lower/upper bounds, steps, reductions, and result type checks |
| `affine.load/store/vector_load/vector_store` | memref/vector element typing, map/index operand checks |
| `affine.min/max` | variadic affine-map operands, index result typing |
| `affine.prefetch` | memref/index map syntax plus locality/cache metadata |
| `affine.dma_start/dma_wait` | memory operand groups, tag operands, stride/size operands, side-effect syntax records |
| `affine.delinearize_index/linearize_index` | index transform operands, static/dynamic basis handling, multi-result/index result checks |
| `affine.yield` | terminator for affine region-owning operations |

The affine parser/printer must support MLIR's dimension and symbol use lists:
`(dims)[symbols]`. Verification must distinguish invalid symbol uses from
invalid dimension uses because later affine analyses depend on that distinction.

### Minimal MemRef And Vector Type Substrate

Affine memory operations require memref and vector types even though broad
memref/vector dialect behavior is not part of the first compiler slice. The
first slice therefore owns a narrow type substrate:

```text
MemRefType(element_type, shape, layout=None, memory_space=None)
VectorType(element_type, shape)
```

Contracts:

- `MemRefType` verifies ranked and unranked memref spelling used by affine
  load/store examples, including dynamic dimensions spelled `?`.
- `VectorType` verifies element type and static vector shape for
  `affine.vector_load` and `affine.vector_store`.
- Affine load/store verification reads only type shape, rank, element type,
  layout, and memory-space metadata. It does not require allocation, subview,
  cast, transfer, vector arithmetic, or bufferization operations.
- A memory operation's affine map result count must match the memref rank unless
  the operation contract explicitly documents a special case.
- `affine.load` and `affine.store` element values must match the memref element
  type. `affine.vector_load` and `affine.vector_store` values must match a
  `VectorType` whose element type matches the memref element type.

Follow-up memref/vector dialect implementation may replace or extend these
classes, but it must preserve the type identity and verification contracts used
by first-slice affine operations.

## Copy Boundary

Candidate xDSL concepts to copy and adjust:

| xDSL Concept | IntelliC Use | Copy Stance |
| --- | --- | --- |
| `Operation` | Base operation storage, parent links, operands, results | Copy and adjust |
| `Region` and `Block` | Nested IR and CFG structure | Copy and adjust |
| `SSAValue`, `OpResult`, `BlockArgument`, `Use` | SSA identity and use tracking | Copy and adjust |
| `Attribute`, `TypeAttribute` | Immutable compile-time data and value types | Copy and adjust |
| `Parser` and `Printer` | Strict canonical IR text | Copy and adjust for IntelliC package/API |
| Dialect/context registration | Operation/type/attribute lookup | Copy ideas and simplify where useful |

Do not expose upstream xDSL modules as the IntelliC public API. Native IntelliC code owns
the architecture after copying.

## Contracts

- Every operation has a fully qualified dialect name.
- Every operation is owned by exactly one block, except detached construction
  during parsing/building.
- Every region is owned by exactly one operation.
- Every value is either an operation result or block argument.
- Every value has one immutable type.
- Attributes and types are immutable once created.
- Structural verification runs before semantic verification.
- Canonical text must round-trip without changing structural meaning.
- `ir_parser` strictly follows MLIR/xDSL syntax.
- `surface_api` constructs native `Sy` objects through Python builders,
  decorators, and insertion contexts.
- Surface construction does not require Python AST parsing or parser-level
  composition.
- Symbolic IR values must not silently drive host Python control flow.
- Every operator hook has an equivalent named builder.
- Every construction API emits construction evidence.
- Syntax does not define execution meaning. It links to semantic mechanisms but
  does not hide semantics inside parser state.

## Failure Modes

- Unknown operation name: parser or verifier fails with dialect/op context.
- Broken use list or parent link: structural verifier fails.
- Value type mismatch: structural verifier fails before semantic execution.
- Non-MLIR/xDSL operation syntax reaches `ir_parser`: parse fails.
- Non-round-tripping text: syntax evidence fails.
- A surface builder emits malformed parent links, use lists, or region
  ownership: structural verifier fails.
- A dialect builder runs without an active insertion point: builder diagnostic
  fails unless detached construction was explicitly requested.
- `func.ir_function` sees missing or unsupported annotations: staging fails with
  a signature diagnostic before emitting a partial function.
- A function or region lacks a required terminator: structural verifier fails.
- An operator hook has no active construction-policy rule for the operand types: surface API
  fails and suggests the named builder form.
- A symbolic `Value` is used as a Python `bool`: surface API fails with a
  diagnostic that asks for explicit IR control-flow builders.
- Copied xDSL behavior conflicts with IntelliC semantics/evidence requirements:
  copied code is adjusted behind the native IntelliC API.

## Examples

### Example 1: Canonical IR Uses Real Dialects

```mlir
"builtin.module"() ({
  func.func @sum_to_n(%n: index) -> i32 {
    %c0_i = arith.constant 0 : index
    %c1_i = arith.constant 1 : index
    %c0 = arith.constant 0 : i32
    %sum = scf.for %i = %c0_i to %n step %c1_i
        iter_args(%total = %c0) -> (i32) {
      %i32 = arith.index_cast %i : index to i32
      %next = arith.addi %total, %i32 : i32
      scf.yield %next : i32
    }
    func.return %sum : i32
  }
}) : () -> ()
```

Feature shown: examples use existing MLIR-style dialect names, not
infrastructure-name-prefixed placeholder operations. The canonical text also
contains nested regions, loop-carried block arguments, and a terminator, so it
exercises more than straight-line operation parsing.

Verification mapping: `ir_parser` parses the module; printer emits canonical
MLIR/xDSL-compatible text; focused reread checks dialect names and region
syntax.

### Example 2: Python Surface Constructs IR Without Parsing

Surface:

```python
@func.ir_function
def sum_to_n(n: index) -> i32:
    zero_i = arith.constant(0, index)
    one_i = arith.constant(1, index)
    zero = arith.constant(0, i32)

    with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
        i, total = loop.arguments
        scf.yield_(arith.addi(total, arith.index_cast(i, i32)))

    return loop.results[0]
```

Construction flow:

```text
func.ir_function
  -> create symbolic block argument %n: index
  -> execute Python body under insertion context
  -> scf.for_ creates a nested body region and loop-carried arguments
  -> arith builders construct index_cast and addi in the loop body
  -> scf.yield_ terminates the body region
  -> native Sy objects
  -> ir_parser round-trip
  -> Sy structural verifier
```

Feature shown: the Python surface composes builders, decorators, and value
hooks instead of a Python source parser. The IR parser stays strict.

Verification mapping: construction evidence maps builder/decorator calls to
emitted operations, including nested region construction, and round-trip
evidence checks the strict IR parser.

### Example 3: Symbolic Control Flow Is Explicit

Surface:

```python
@func.ir_function
def sum_to_n(n: index) -> i32:
    zero_i = arith.constant(0, index)
    one_i = arith.constant(1, index)
    zero = arith.constant(0, i32)

    with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
        i, total = loop.arguments
        total_next = arith.addi(total, arith.index_cast(i, i32))
        scf.yield_(total_next)

    return loop.results[0]
```

Feature shown: symbolic control flow uses IR region builders. The design does not
try to parse Python `for` loops or reinterpret host Python control flow. The
`scf.for_` helper explicitly creates the operation, body region, induction
variable block argument, loop-carried block arguments, `scf.yield`, and loop
results.

Verification mapping: construction evidence shows `scf.for` owns one body
region, block argument order is `(iv, iter_args...)`, `scf.yield` value count
matches loop result count, and structural verification checks loop-carried
argument/result ownership.

### Example 4: Named Builders Are The Ground Truth

Surface:

```python
@func.ir_function
def sum_to_n_explicit(n: index) -> i32:
    zero_i = arith.constant(0, index)
    one_i = arith.constant(1, index)
    zero = arith.constant(0, i32)
    with scf.for_(zero_i, n, one_i, iter_args=(zero,)) as loop:
        i, total = loop.arguments
        i32 = arith.index_cast(i, i32)
        next_total = arith.addi(total, i32)
        scf.yield_(next_total)
    return loop.results[0]
```

Feature shown: operator sugar is optional. The named builder path remains the
canonical Python construction API and is the fallback when an operator hook or
region helper shortcut is ambiguous or unavailable.

Verification mapping: construction evidence records the `arith.constant`,
`arith.index_cast`, `arith.addi`, `scf.for_`, and `scf.yield_` builder calls and
maps them to emitted operations.

### Example 5: Affine Tiled Access Uses Dimensions And Symbols

Canonical IR sketch:

```mlir
#tile = affine_map<(d0, d1)[s0] -> (d0 * 16 + d1 + s0)>

func.func @affine_tile(%A: memref<?xf32>, %N: index, %offset: index) {
  affine.for %tile = 0 to %N step 16 {
    affine.for %ii = 0 to 16 {
      %idx = affine.apply #tile(%tile, %ii)[%offset]
      %v = affine.load %A[%idx] : memref<?xf32>
      affine.store %v, %A[%idx] : memref<?xf32>
    }
  }
  func.return
}
```

Feature shown: affine syntax distinguishes dimensions `(%tile, %ii)` from
symbols `[%offset]`, carries affine maps through apply/load/store operations,
and nests affine loops with canonical region ownership.

Verification mapping: `tests/test_affine_syntax.py` parses and prints the map
definition, rejects a map operand count mismatch, rejects an invalid symbol use,
and verifies that load/store element types match the memref element type.

## First Syntax Implementation Slice

The first syntax implementation should be large enough to reuse xDSL's proven
syntax design instead of rediscovering it in tiny increments. Syntax is the
lowest-risk part of the compiler framework because IntelliC can copy/adapt the
xDSL object, parser, printer, and dialect-registration substrate behind native
IntelliC APIs.

```text
Input:
  Canonical MLIR/xDSL-compatible IR text using builtin.module, func.func,
  func.return, arith.constant, arith.addi, arith.index_cast, full scf syntax,
  affine.apply, affine.for, affine.if, affine.load/store, affine.min/max,
  minimal memref/vector types, simple blocks, loop-carried block arguments,
  and nested regions

  Python construction API examples using builtin.module, func.ir_function,
  func.return_, arith.constant, arith.addi, arith.index_cast, scf builders,
  affine builders/map constructors, Value.__add__, and construction evidence

Output:
  Native Sy object graph with Operation, Region, Block, Value, Use, Type,
  Attribute, SourceLocation, and Dialect/Context ownership

  construction evidence

  canonical MLIR/xDSL-compatible text

Verification:
  strict ir_parser parses generic operation form and the selected custom forms
  printer/parser round-trip preserves structure and operation identities
  structural verifier checks parent links, region ownership, block arguments,
  use lists, result types, and terminators
  Python builders/decorator produce the same structural IR as the canonical text,
  including nested `scf` regions, loop-carried block arguments, and affine map
  operands
  construction evidence maps each Python builder call to emitted operations
  negative parser and builder diagnostics are exercised
```

Included in the first slice:

- xDSL-derived `Operation`, `Region`, `Block`, `Value`, `Use`, `Type`,
  `Attribute`, `Context`, `Dialect`, parser, printer, and structural verifier.
- Builtin, func, arith, full scf, and affine syntax sufficient for examples and
  for the first implementation plan.
- Generic operation parsing/printing and the small selected custom forms needed
  for examples.
- Builder and insertion-point APIs.
- `func.ir_function` staging for straight-line functions and the first
  `scf.for_` loop-carried example.
- Named builders for `builtin.module`, `func.func`, `func.return_`,
  `arith.constant`, `arith.addi`, `arith.index_cast`, `scf.for_`, and
  `scf.yield_`; full SCF builders may land in batches but their contracts are
  defined here.
- Affine expression/map/set constructors and named builders for `affine.apply`,
  `affine.for_`, `affine.if_`, `affine.load`, `affine.store`, `affine.min`,
  and `affine.max`.
- Minimal `MemRefType` and `VectorType` construction/parsing sufficient for
  affine load/store/vector_load/vector_store type verification.
- Basic operator sugar for `Value.__add__` when the active construction policy maps it to
  `arith.addi`.
- Construction evidence for builder/decorator/operator-hook calls.

Still follow-up work:

- Full MLIR/xDSL custom assembly coverage beyond the selected example forms.
- `cf.br`, comparison hooks, broad memref/vector dialect implementation, and
  optimized affine transformations beyond the first affine proof points.
- Declarative operation-definition machinery.
- Semantic execution, pass scheduling, and action database history.
- Backend lowering.

## Implementation-Ready Module Contracts

The first syntax implementation should expose these modules and contracts:

```text
intellic/ir/syntax/
  ids.py             # stable internal ids for operations, values, blocks, regions
  location.py        # source/generated/evidence locations
  type.py            # immutable Type base and builtin integer/index types
  attribute.py       # immutable Attribute base and builtin attrs
  value.py           # Value, OpResult, BlockArgument, Use
  operation.py       # Operation.create, result ownership, operand replacement
  region.py          # Region, Block, parent ownership, terminator queries
  builder.py         # Builder, InsertionPoint, controlled insertion/mutation
  verify.py          # structural verifier and diagnostics
  context.py         # Context, Dialect registration, operation lookup
  printer.py         # canonical generic/custom printing

intellic/ir/dialects/
  builtin.py         # module op, builtin attrs/types needed by examples
  func.py            # func.func, func.return, function type helpers
  arith.py           # arith.constant, arith.addi, integer attrs/types
  scf.py             # full structured-control-flow dialect
  affine.py          # affine expressions, maps, sets, and affine ops
  memref.py          # type-only first-slice MemRefType substrate
  vector.py          # type-only first-slice VectorType substrate

intellic/ir/parser/
  lexer.py           # copied/adapted MLIR lexer behavior
  parser.py          # canonical IR parser for selected generic/custom forms

intellic/surfaces/api/
  builders.py        # active builder stack and construction evidence
  func.py            # func.ir_function decorator facade
  arith.py           # named builders and optional operator policy
  scf.py             # region helpers for all SCF operations
  affine.py          # affine expression/map/set helpers and affine op builders
```

First-slice invariants:

- An operation has at most one parent block. Detached operations have no parent.
- A block has at most one parent region. A region has at most one parent
  operation unless it is a top-level detached region during construction.
- Operation operands are updated only through controlled APIs that keep `Use`
  records consistent.
- Printed SSA and block names are presentation names; identity comes from
  objects and stable internal ids.
- Types and attributes are immutable after construction.
- Direct list mutation of operation, block, and region children is not public.
- A builder insertion point is scoped and explicit; named builders fail without
  one unless documented to return a detached operation.

First-slice failure tests:

- parse rejects noncanonical syntax and unknown operations unless generic form
  plus registered dialect rules allow them.
- verifier rejects broken parent links, wrong region counts, missing
  terminators, type mismatches, and stale uses.
- builder rejects insertion without an insertion point, reparenting without an
  explicit mutation API, and host Python boolean use of symbolic values.
- `func.ir_function` rejects missing annotations, unsupported Python control
  flow over symbolic values, and returns that cannot be lowered to
  `func.return`.
- SCF verification rejects missing required regions, invalid terminator
  placement, mismatched yield/result counts, invalid reduction region types,
  invalid `scf.condition` payloads, and malformed `scf.forall.in_parallel`.
- Affine verification rejects dimension/symbol operand count mismatches,
  invalid symbol binding, non-positive affine loop steps, memory element type
  mismatches, rank/map-result mismatches, vector element mismatches, and
  malformed affine DMA/prefetch operand groups.

## Acceptance Criteria

- The first implementation slice includes xDSL-derived syntax core, parser,
  printer, dialect/context registration, structural verifier, and construction
  APIs behind native IntelliC package names.
- The minimal `Operation`, `Region`, `Block`, `Value`, `Use`, `Type`,
  `Attribute`, `Builder`, and `SourceLocation` contracts are explicit enough for
  implementation.
- Python construction APIs are defined as builders/decorators/hooks over `Sy`,
  not as source parsing.
- `func.ir_function` staging has a concrete argument, return, terminator, and
  verification contract.
- Symbolic control flow is explicit through region helpers; host Python boolean
  control flow over symbolic values is rejected.
- Full SCF coverage and affine dialect coverage are concrete enough to implement
  in batches without changing public contracts.
- The first-slice memref/vector substrate is narrow but sufficient for affine
  memory operation verification.
- Examples cover canonical IR parsing, Python builder construction, operator
  sugar, explicit region helpers, affine map/set syntax, and affine access facts.
- Each example names verification evidence before implementation.

## Planned Verification Evidence

- Reference-map path check for linked xDSL and MLIR source/docs.
- Focused reread of copied xDSL classes before implementation.
- Parser golden evidence for canonical MLIR/xDSL examples.
- Surface construction evidence for decorator, builder, operator-hook, and
  region-helper examples.
- Round-trip evidence for generic and custom operation forms.
- Structural verifier evidence for parent links, use lists, and type mismatch.
- Negative construction evidence for missing insertion point, missing function
  annotations, missing terminator, unsupported operator hook, and symbolic
  boolean use.
- SCF parser/verifier evidence for every SCF operation family, including
  `scf.forall` even though the current xDSL checkout does not expose it.
- Affine parser/verifier evidence for maps, sets, apply, min/max, loops,
  conditionals, parallelism, memory ops, DMA/prefetch, and index transforms.

## Out Of Scope

- Execution semantics.
- Pass scheduling and semantic action execution.
- Declarative operation-definition machinery as a required first concept.
- Parser-level composition for Pythonic source surfaces.
- Treating xDSL as a runtime wrapper dependency for IntelliC's public API.
