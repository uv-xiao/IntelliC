# PTO PyPTO-Inspired SwiGLU

This example uses the traced `@kernel` surface to express a fused activation
kernel with three staged elementwise operations:

1. `sigmoid(gate)`
2. `gate * sigmoid(gate)`
3. `swish(gate) * up`

The package targets `pto-a2a3sim` and exercises the real PTO runtime adapter.
