# Conventions

- Code/comments/identifiers should stay English unless existing domain content requires Spanish labels/prompts.
- Backend currently uses module-level FastAPI functions and plain JSON persistence; keep changes small unless intentionally migrating architecture.
- Frontend uses React components under `frontend/src/components/`; prefer TypeScript interfaces for object shapes and avoid `any`.
- Keep model/worldview definitions centralized in backend config; do not hardcode provider/model details in request handling or UI logic.
- Preserve immediate disk persistence semantics for question mutations unless a change explicitly introduces transactions/rollback.
- Avoid unrelated refactors; this app is small and benefits from reviewable slices around one flow at a time.