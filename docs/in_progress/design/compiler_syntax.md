# Design: Compiler Syntax

> Review status: Draft only. Not reviewed or approved. This document records
> current working direction and fix advice for IntelliC; do not treat it as
> accepted architecture until explicit human review approves it.

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

## Parser Split

IntelliC has two parser families:

```text
surface_parser:
  modular parsers for human/LLM-facing source surfaces
  lower into canonical IR
  share diagnostics, source capture, symbol/lowering helpers, and evidence

ir_parser:
  canonical IR parser
  copied/adapted from xDSL's existing MLIR-compatible parser
  strictly follows MLIR/xDSL operation, region, block, type, and attribute syntax
```

The parsers share lower-level utilities where that improves consistency, but
they are not the same layer. A surface parser may accept Pythonic forms. The IR
parser must accept canonical IR text and reject noncanonical syntax.

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

Type / Attribute
  immutable compile-time objects
```

This mirrors MLIR/xDSL because those projects already solved many structural
problems: SSA use lists, nested regions, block arguments, dialect namespaces,
custom assembly, generic operation syntax, and open type/attribute systems.

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

If IntelliC later adds domain dialects, those dialects need their own design docs.

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
- `surface_parser` lowers into canonical IR and records source evidence.
- Syntax does not define execution meaning. It links to semantic mechanisms but
  does not hide semantics inside parser state.

## Failure Modes

- Unknown operation name: parser or verifier fails with dialect/op context.
- Broken use list or parent link: structural verifier fails.
- Value type mismatch: structural verifier fails before semantic execution.
- Non-MLIR/xDSL operation syntax reaches `ir_parser`: parse fails.
- Non-round-tripping text: syntax evidence fails.
- Copied xDSL behavior conflicts with IntelliC semantics/evidence requirements:
  copied code is adjusted behind the native IntelliC API.

## Examples

### Example 1: Canonical IR Uses Real Dialects

```mlir
"builtin.module"() ({
  func.func @add_one(%x: i32) -> i32 {
    %c1 = arith.constant 1 : i32
    %y = arith.addi %x, %c1 : i32
    func.return %y : i32
  }
}) : () -> ()
```

Feature shown: examples use existing MLIR-style dialect names, not
infrastructure-name-prefixed placeholder operations.

Verification mapping: `ir_parser` parses the module; printer emits canonical
MLIR/xDSL-compatible text; focused reread checks dialect names.

### Example 2: Parser Responsibilities Stay Separate

Surface:

```python
@surface
def add_one(x: i32) -> i32:
    return x + 1
```

Parser flow:

```text
surface_parser.python
  -> canonical IR text or native Sy objects
  -> ir_parser round-trip
  -> Sy structural verifier
```

Feature shown: a surface parser can be Pythonic and modular, while the IR
parser stays strict.

Verification mapping: source-evidence check for surface lowering and round-trip
check for IR parser.

## Planned Verification Evidence

- Focused reread of copied xDSL classes before implementation.
- Parser golden evidence for canonical MLIR/xDSL examples.
- Round-trip evidence for generic and custom operation forms.
- Structural verifier evidence for parent links, use lists, and type mismatch.

## Out Of Scope

- Execution semantics.
- Pass scheduling and semantic action execution.
- Declarative operation-definition machinery as a required first concept.
- Treating xDSL as a runtime wrapper dependency for IntelliC's public API.
