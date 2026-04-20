# Security And Environment Rules

- Do not commit secrets, credentials, tokens, private endpoints, or machine-specific absolute paths.
- Use project-relative paths in docs and scripts.
- Do not commit `.references/`, `.repositories/`, virtual environments, caches, generated packages, or local build output.
- Create and use a project-local virtual environment before running install or package-management commands.
- Do not install into the user or global Python environment.
- Ask before adding dependencies or changing CI/runtime environment assumptions.
- If hardware, credentials, or external services are unavailable, skip explicitly with a documented reason rather than faking success.
