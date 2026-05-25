# Frontend Core

- Entry point: `frontend/src/App.tsx`; currently owns bootstrap loading, slots, current question, loading/errors, and response state.
- API client/types: `frontend/src/api.ts` and `frontend/src/types.ts`.
- Main components: `QuestionCard`, `SlotConfigurator`, `ResultsTable`, `QuestionFormModal`, `UploadButton`, `ExportButton`.
- App bootstraps questions/models/worldviews, renders current question, lets user configure model/worldview slots, then calls backend `/api/ask`.
- Known UX gotchas: zero-question state can look like loading; question image rendering can indirectly trigger backend image generation; slots reset on reload because no local persistence detected.
- Improvement seam: extract hooks for bootstrap data and ask flow before large UI changes.