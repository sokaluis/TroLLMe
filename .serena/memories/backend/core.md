# Backend Core

- Entry point: `backend/main.py` defines FastAPI app and REST endpoints.
- Config/catalog: `backend/config.py` holds available models and worldview prompts.
- LLM flow: `backend/llm_service.py` assembles prompts and calls OpenRouter.
- Persistence: `backend/storage.py` manages response history JSON and dedupe behavior.
- Schemas: `backend/models.py` contains Pydantic request/response models.
- Questions: loaded from and written back to `backend/questions.json`; app also keeps module/global in-memory questions state.
- Critical gotchas discovered: image GET endpoint may generate/cache images as a side effect; response dedupe by `(question_hash, model_id, worldview_id)` can make an earlier error block a later successful retry; JSON + globals are fragile for multi-worker/concurrent deployments.