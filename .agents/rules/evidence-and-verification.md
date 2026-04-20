# Evidence And Verification Rules

- Every feature task needs explicit input, output, and verification criteria.
- Design drafts must include concrete examples that show feature behavior.
- Design examples must map to tests or evidence before implementation starts.
- Design verification before implementation whenever behavior can be tested or demonstrated.
- Use minimal reproducible demos before debugging a complex system through broad code search.
- Do not claim work is complete, fixed, or passing without fresh command output from the relevant verification.
- Prefer focused verification first, then broader checks.
- Documentation-only changes do not require automated tests.
- Documentation-only changes still require concrete verification evidence, such as
  a focused reread, link/path check, policy check, or rendered-doc inspection.
- A PR with code or behavior changes must include tests or a documented reason tests are impossible for the current scope.
- Do not weaken tests, assertions, or policy checks to make CI pass unless the contract intentionally changed and docs are updated.
- Capture exact verification commands in task files, PR bodies, or handoff notes.
