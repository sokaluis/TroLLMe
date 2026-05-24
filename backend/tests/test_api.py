"""API-level integration test for the ask endpoint dedupe flow.

Validates that the storage dedupe semantics work end-to-end through
the FastAPI ask route with a mocked LLM boundary.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import storage
from main import app
from models import ModelResponse


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_data(monkeypatch: pytest.MonkeyPatch):
    """Isolate questions.json and responses.json for the test."""
    tmp = tempfile.mkdtemp(prefix="trollme-api-test-")

    questions_path = os.path.join(tmp, "questions.json")
    with open(questions_path, "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "id": 1,
                    "title": "Test Question",
                    "prompt": "Save one or five?",
                    "options": ["Save one", "Save five"],
                }
            ],
            f,
        )

    monkeypatch.setattr("main.QUESTIONS_FILE", questions_path)

    # Redirect storage persistence
    resp_file = os.path.join(tmp, "responses.json")
    monkeypatch.setattr(storage, "DATA_DIR", tmp)
    monkeypatch.setattr(storage, "RESPONSES_FILE", resp_file)

    yield tmp

    for root, dirs, files in os.walk(tmp, topdown=False):
        for name in files:
            os.unlink(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(tmp)


@pytest.fixture
def client(temp_data: str) -> TestClient:
    """TestClient with isolated storage. Loads questions from temp file on startup."""
    # Force reload of startup questions
    import main

    main._questions = main._load_questions_from_file(main.QUESTIONS_FILE)
    with TestClient(app) as c:
        yield c


def _mock_success_response(
    slot_id: str = "s1", model_id: str = "m1", worldview_id: str = "w1"
) -> ModelResponse:
    return ModelResponse(
        slot_id=slot_id,
        model_id=model_id,
        display_name="Mock Model",
        worldview_id=worldview_id,
        worldview_label="Mock View",
        choice="Save one",
        reasoning="Because reasons.",
        moral_framework="test",
    )


def _mock_error_response(
    slot_id: str = "s1", model_id: str = "m1", worldview_id: str = "w1"
) -> ModelResponse:
    return ModelResponse(
        slot_id=slot_id,
        model_id=model_id,
        display_name="Mock Model",
        worldview_id=worldview_id,
        worldview_label="Mock View",
        error="Simulated failure",
    )


# ---------------------------------------------------------------------------
# dedupe through /api/ask
# ---------------------------------------------------------------------------


class TestAskDedupeFlow:
    """Verify that the retry-after-error dedupe fix works through the API."""

    def test_error_then_success_through_api(self, client: TestClient):
        """Error response → retry with success → both stored, third blocked."""
        slot = {"slot_id": "s1", "model_id": "m1", "worldview_id": "w1"}
        payload = {"question_id": 1, "slots": [slot]}

        with patch(
            "main.ask_slots",
            new_callable=AsyncMock,
            return_value=[_mock_error_response()],
        ):
            resp1 = client.post("/api/ask", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["responses"][0]["error"] == "Simulated failure"

        with patch(
            "main.ask_slots",
            new_callable=AsyncMock,
            return_value=[_mock_success_response()],
        ):
            resp2 = client.post("/api/ask", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["responses"][0]["error"] is None

        # Third call (same success) should be blocked by prior success
        with patch(
            "main.ask_slots",
            new_callable=AsyncMock,
            return_value=[_mock_success_response()],
        ):
            resp3 = client.post("/api/ask", json=payload)
        assert resp3.status_code == 200
        data3 = resp3.json()
        # The response should still appear in AskResponse (it's in-memory)
        # but storage should NOT have persisted it
        assert data3["responses"][0]["choice"] == "Save one"

        # Verify persistence: only 2 records (error + 1 success)
        all_resp = client.get("/api/responses").json()
        assert len(all_resp) == 2, f"Expected 2 persisted records, got {len(all_resp)}"
        errors = [r for r in all_resp if r["error"]]
        successes = [r for r in all_resp if not r["error"]]
        assert len(errors) == 1
        assert len(successes) == 1

    def test_success_blocks_duplicate_through_api(self, client: TestClient):
        """Success → same success → only one persisted."""
        slot = {"slot_id": "s1", "model_id": "m1", "worldview_id": "w1"}
        payload = {"question_id": 1, "slots": [slot]}

        with patch(
            "main.ask_slots",
            new_callable=AsyncMock,
            return_value=[_mock_success_response()],
        ):
            client.post("/api/ask", json=payload)
            client.post("/api/ask", json=payload)

        all_resp = client.get("/api/responses").json()
        assert len(all_resp) == 1
