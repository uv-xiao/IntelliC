# Evidence And Verification Rules

- Every feature task needs explicit input, output, and verification criteria.
- Design verification before implementation whenever behavior can be tested or demonstrated.
- Use minimal reproducible demos before debugging a complex system through broad code search.
- Do not claim work is complete, fixed, or passing without fresh command output from the relevant verification.
- Prefer focused verification first, then broader checks.
- A PR must include tests or a documented reason tests are impossible for the current scope.
- Do not weaken tests, assertions, or policy checks to make CI pass unless the contract intentionally changed and docs are updated.
- Capture exact verification commands in task files, PR bodies, or handoff notes.
