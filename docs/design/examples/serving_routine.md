# Serving Routine Example

Code anchor: `examples/workloads/serving_routine/demo.py`

This example demonstrates a workload-level routine above the current kernel
examples:

- a public routine surface built with `htp.kernel` and `htp.routine`
- multiple named tasks across prefill, iterative decode, sampling, and writeback
- explicit inter-task dependencies
- typed FIFO channels that survive into staged `workload_ir.json`
- replay of the final staged Python program
- inspection of `workload_ir.json` as the backend-facing routine contract

What it proves:

- higher-level routine authoring can stay Python-native instead of collapsing
  into a raw program dict
- kernel bodies inside the routine can use expression-form authoring such as
  `store(next_hidden, hidden @ weights)`
- the compiler keeps workload structure explicit in staged artifacts
- routine structure is visible to replay, diagnostics, and backend-facing
  lowering sidecars
- the routine can be authored as ordinary Python control flow plus `call(...)`
  edges instead of a prebuilt task-list payload
