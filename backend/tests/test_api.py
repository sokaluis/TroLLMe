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
    """Isolate questions.json, responses.json, and images directory for the test."""
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

    # Isolate image cache directory
    images_dir = os.path.join(tmp, "images")
    monkeypatch.setattr("main.IMAGES_DIR", images_dir)

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
    slot_id: str = "s1",
    model_id: str = "openai/gpt-4o",
    worldview_id: str = "neutral",
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
    slot_id: str = "s1",
    model_id: str = "openai/gpt-4o",
    worldview_id: str = "neutral",
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
        slot = {"slot_id": "s1", "model_id": "openai/gpt-4o", "worldview_id": "neutral"}
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
        slot = {"slot_id": "s1", "model_id": "openai/gpt-4o", "worldview_id": "neutral"}
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


# ---------------------------------------------------------------------------
# image API boundary — GET must be read-only; POST generates
# ---------------------------------------------------------------------------


class TestImageApiBoundary:
    """Verify GET image never triggers generation; POST does."""

    @pytest.fixture
    def _fake_image_bytes(self) -> bytes:
        return b"\xff\xd8\x00\x00fake jpeg data"

    def test_get_image_cache_miss_returns_404(
        self, client: TestClient, _fake_image_bytes: bytes
    ):
        """GET without cached image MUST return 404 and NOT call LLM."""
        with patch(
            "main.generate_question_image",
            new_callable=AsyncMock,
            return_value=_fake_image_bytes,
        ) as mock_gen:
            resp = client.get("/api/questions/1/image")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "No cached image" in data["detail"]
        mock_gen.assert_not_called()

    def test_post_image_generates_and_caches(
        self, client: TestClient, _fake_image_bytes: bytes
    ):
        """POST generates image, caches it, and returns metadata."""
        with patch(
            "main.generate_question_image",
            new_callable=AsyncMock,
            return_value=_fake_image_bytes,
        ) as mock_gen:
            resp = client.post("/api/questions/1/image")
        assert resp.status_code == 200
        data = resp.json()
        assert data["question_id"] == 1
        assert data["cached"] is True
        assert data["media_type"] == "image/jpeg"
        mock_gen.assert_called_once()

        # Subsequent GET should now return the cached image
        resp_get = client.get("/api/questions/1/image")
        assert resp_get.status_code == 200
        assert resp_get.content == _fake_image_bytes

    def test_post_image_404_for_unknown_question(self, client: TestClient):
        resp = client.post("/api/questions/999/image")
        assert resp.status_code == 404

    def test_get_image_404_for_unknown_question(self, client: TestClient):
        resp = client.get("/api/questions/999/image")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# catalog validation — unknown model_id / worldview_id → 422
# ---------------------------------------------------------------------------


class TestCatalogValidation:
    """Invalid model_id or worldview_id must return 422 before any LLM call."""

    def test_unknown_model_id_rejected(self, client: TestClient):
        slot = {"slot_id": "s1", "model_id": "nonexistent/model", "worldview_id": "neutral"}
        payload = {"question_id": 1, "slots": [slot]}

        with patch("main.ask_slots", new_callable=AsyncMock) as mock_ask:
            resp = client.post("/api/ask", json=payload)
        assert resp.status_code == 422
        data = resp.json()
        assert "Unknown model_id" in data["detail"]
        mock_ask.assert_not_called()

    def test_unknown_worldview_id_rejected(self, client: TestClient):
        slot = {"slot_id": "s1", "model_id": "openai/gpt-4o", "worldview_id": "fake_view"}
        payload = {"question_id": 1, "slots": [slot]}

        with patch("main.ask_slots", new_callable=AsyncMock) as mock_ask:
            resp = client.post("/api/ask", json=payload)
        assert resp.status_code == 422
        data = resp.json()
        assert "Unknown worldview_id" in data["detail"]
        mock_ask.assert_not_called()

    def test_valid_catalog_ids_proceed(self, client: TestClient):
        """Sanity: valid catalog IDs should still reach ask_slots."""
        slot = {"slot_id": "s1", "model_id": "openai/gpt-4o", "worldview_id": "neutral"}
        payload = {"question_id": 1, "slots": [slot]}

        with patch(
            "main.ask_slots",
            new_callable=AsyncMock,
            return_value=[_mock_success_response()],
        ) as mock_ask:
            resp = client.post("/api/ask", json=payload)
        assert resp.status_code == 200
        mock_ask.assert_called_once()


# ---------------------------------------------------------------------------
# question create / update validation
# ---------------------------------------------------------------------------


class TestQuestionValidation:
    """Create and update endpoints must reject malformed payloads with 422."""

    def test_create_blank_title(self, client: TestClient):
        resp = client.post(
            "/api/questions",
            json={"title": "  ", "prompt": "Valid prompt?", "options": ["A", "B"]},
        )
        assert resp.status_code == 422

    def test_create_blank_prompt(self, client: TestClient):
        resp = client.post(
            "/api/questions",
            json={"title": "Valid", "prompt": "", "options": ["A", "B"]},
        )
        assert resp.status_code == 422

    def test_create_too_few_options(self, client: TestClient):
        resp = client.post(
            "/api/questions",
            json={"title": "Valid", "prompt": "Valid?", "options": ["Only one"]},
        )
        assert resp.status_code == 422

    def test_create_duplicate_options(self, client: TestClient):
        resp = client.post(
            "/api/questions",
            json={"title": "Valid", "prompt": "Valid?", "options": ["A", "A"]},
        )
        assert resp.status_code == 422

    def test_create_valid_payload(self, client: TestClient):
        resp = client.post(
            "/api/questions",
            json={"title": "New Q", "prompt": "Save one?", "options": ["One", "Five"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Q"
        assert data["options"] == ["One", "Five"]

    def test_update_blank_title(self, client: TestClient):
        resp = client.put(
            "/api/questions/1",
            json={"title": "   "},
        )
        assert resp.status_code == 422

    def test_update_duplicate_options(self, client: TestClient):
        resp = client.put(
            "/api/questions/1",
            json={"options": ["X", "X"]},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# upload atomicity
# ---------------------------------------------------------------------------


class TestUploadAtomicity:
    """Upload must validate all rows before replacing questions."""

    def test_valid_json_upload_replaces_questions(self, client: TestClient):
        payload = [
            {"id": 1, "title": "Q1", "prompt": "First?", "options": ["A", "B"]},
            {"id": 2, "title": "Q2", "prompt": "Second?", "options": ["C", "D"]},
        ]
        resp = client.post(
            "/api/questions/upload",
            files={"file": ("questions.json", json.dumps(payload), "application/json")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["title"] == "Q1"

        # Verify persisted
        all_q = client.get("/api/questions").json()
        assert len(all_q) == 2

    def test_invalid_row_preserves_existing_questions(self, client: TestClient):
        """An invalid row must fail with 422 and NOT replace existing questions."""
        # First, verify the current questions exist (the fixture provides one)
        before = client.get("/api/questions").json()
        assert len(before) == 1

        payload = [
            {"id": 10, "title": "Good", "prompt": "Good?", "options": ["A", "B"]},
            {"id": 11, "title": "", "prompt": "Bad", "options": ["C"]},  # blank title + too few options
        ]
        resp = client.post(
            "/api/questions/upload",
            files={"file": ("questions.json", json.dumps(payload), "application/json")},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "Row 1" in data["detail"]

        # Existing questions must be unchanged
        after = client.get("/api/questions").json()
        assert len(after) == 1
        assert after[0]["id"] == 1

    def test_valid_csv_upload_replaces_questions(self, client: TestClient):
        csv_content = "id,title,prompt,options\n1,Q1,First?,A;B\n2,Q2,Second?,C;D\n"
        resp = client.post(
            "/api/questions/upload",
            files={"file": ("questions.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_invalid_csv_row_preserves_existing(self, client: TestClient):
        before = client.get("/api/questions").json()
        assert len(before) == 1

        csv_content = "id,title,prompt,options\n10,Good,Good?,A;B\n11,,Bad,\n"
        resp = client.post(
            "/api/questions/upload",
            files={"file": ("questions.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 422
        # Existing questions must be unchanged
        after = client.get("/api/questions").json()
        assert len(after) == 1
