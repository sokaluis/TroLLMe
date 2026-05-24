# Suggested Commands

Backend:
- Create venv: `cd backend && python3 -m venv .venv`
- Install deps: `cd backend && .venv/bin/python -m pip install -r requirements.txt`
- Run API: `cd backend && .venv/bin/python -m uvicorn main:app --port 8000 --reload`

Frontend:
- Install deps: `cd frontend && pnpm install`
- Run dev server: `cd frontend && pnpm dev`
- Lint: `cd frontend && pnpm lint`
- Build script exists: `cd frontend && pnpm build` (`tsc -b && vite build`), but do not run builds automatically in assistant sessions.

Useful URLs:
- API: `http://localhost:8000`
- FastAPI docs: `http://localhost:8000/docs`
- UI: `http://localhost:5173`