# Tech Stack

- Backend: Python 3.11+, FastAPI, Uvicorn, Pydantic, httpx, python-dotenv, python-multipart.
- LLM provider: OpenRouter via `OPENROUTER_API_KEY`; model/worldview catalog lives in backend config.
- Persistence: plain JSON files on disk, no DB/migrations yet.
- Frontend: React 19, TypeScript 6, Vite 8, Tailwind CSS v4, ESLint 10.
- Package manager: frontend is pnpm-only, pinned via `packageManager` to pnpm 11.1.2.
- Root project has separate backend/frontend dependency management, no monorepo task runner detected.