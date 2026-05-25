# Task Completion

- Frontend code changes: run `cd frontend && pnpm lint` when dependencies are installed.
- Backend currently has no test script or pytest dependency detected; add focused tests before/with behavioral backend changes.
- For API behavior changes, manually inspect FastAPI docs or exercise endpoint contracts only if needed; avoid live OpenRouter calls unless explicitly requested and credentials/cost are approved.
- Do not run build commands automatically in assistant sessions.
- For Serena memory sanity after onboarding/maintenance: from project root, user can run `serena memories check`.