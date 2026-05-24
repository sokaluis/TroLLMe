# Core

- TroLLMe = side-by-side LLM moral dilemma comparison app using live OpenRouter calls.
- Root modules: `backend/` FastAPI API + JSON persistence; `frontend/` React/Vite UI.
- Data sources: questions in `backend/questions.json`; response history in `backend/data/responses.json`; generated question images cached under backend data/static paths.
- Main flows: UI loads questions/models/worldviews, configures slots, POSTs `/api/ask`, backend calls OpenRouter per slot and appends non-duplicate responses.
- Read backend specifics in `mem:backend/core`; frontend specifics in `mem:frontend/core`.
- Read stack/deps in `mem:tech_stack`, conventions in `mem:conventions`, run commands in `mem:suggested_commands`, completion checks in `mem:task_completion`.