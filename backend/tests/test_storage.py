"""Behavioral tests for storage dedupe semantics.

Covers: compute_question_hash determinism, success-only duplicate suppression,
and error-then-success append flow.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

import storage
from models import ModelResponse, Question


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_data_dir(monkeypatch: pytest.MonkeyPatch) -> str:
    """Redirect storage persistence to an isolated temp directory per test.

    Monkeypatches the module-level DATA_DIR and derived RESPONSES_FILE so
    each test starts with a clean JSON store and cannot leak state into the
    real data/ directory.
    """
    tmp = tempfile.mkdtemp(prefix="trollme-test-")
    monkeypatch.setattr(storage, "DATA_DIR", tmp)
    monkeypatch.setattr(storage, "RESPONSES_FILE", os.path.join(tmp, "responses.json"))
    yield tmp
    # cleanup
    for root, dirs, files in os.walk(tmp, topdown=False):
        for name in files:
            os.unlink(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(tmp)


def _make_question(
    id_: int = 1, title: str = "Test Q", prompt: str = "A or B?", options: list[str] | None = None
) -> Question:
    return Question(id=id_, title=title, prompt=prompt, options=options or ["A", "B"])


def _make_response(
    slot_id: str = "s1",
    model_id: str = "m1",
    worldview_id: str = "w1",
    error: str | None = None,
    choice: str = "A",
) -> ModelResponse:
    return ModelResponse(
        slot_id=slot_id,
        model_id=model_id,
        display_name="Test Model",
        worldview_id=worldview_id,
        worldview_label="Test View",
        choice=choice,
        reasoning="Because.",
        moral_framework="test",
        error=error,
    )


def _raw_records() -> list[dict]:
    """Read the persisted JSON list directly (bypasses model parsing)."""
    path = storage.RESPONSES_FILE
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# compute_question_hash
# ---------------------------------------------------------------------------


class TestComputeQuestionHash:
    def test_same_question_same_hash(self):
        q1 = _make_question(title="Dilema", prompt="Uno o dos?", options=["Uno", "Dos"])
        q2 = _make_question(title="Dilema", prompt="Uno o dos?", options=["Uno", "Dos"])
        assert storage.compute_question_hash(q1) == storage.compute_question_hash(q2)

    def test_different_prompt_different_hash(self):
        q1 = _make_question(prompt="A or B?")
        q2 = _make_question(prompt="C or D?")
        assert storage.compute_question_hash(q1) != storage.compute_question_hash(q2)

    def test_different_options_different_hash(self):
        q1 = _make_question(options=["X", "Y"])
        q2 = _make_question(options=["X", "Z"])
        assert storage.compute_question_hash(q1) != storage.compute_question_hash(q2)

    def test_whitespace_stripped_before_hash(self):
        q1 = _make_question(title="  Foo  ", prompt=" Bar ", options=["  Baz "])
        q2 = _make_question(title="Foo", prompt="Bar", options=["Baz"])
        assert storage.compute_question_hash(q1) == storage.compute_question_hash(q2)


# ---------------------------------------------------------------------------
# dedupe behaviour: success blocks duplicates; errors never block
# ---------------------------------------------------------------------------


class TestSuccessOnlyDedupe:
    """Verify the contract from the design:

    * A stored successful response blocks future duplicates for the same
      (question_hash, model_id, worldview_id).
    * A stored error response does NOT suppress a later successful retry.
    * Once a success is stored, even later identical successes are suppressed.
    """

    def test_success_blocks_duplicate_success(self, temp_data_dir: str):
        """Same successful response is not duplicated."""
        q = _make_question()
        resp = _make_response()

        first = storage.save_response(q, resp)
        second = storage.save_response(q, resp)

        assert first is not None
        assert second is None  # blocked by prior success
        assert len(_raw_records()) == 1

    def test_error_does_not_block_later_success(self, temp_data_dir: str):
        """Error record MUST NOT suppress a subsequent successful retry."""
        q = _make_question()
        error_resp = _make_response(error="timeout", choice=None)
        success_resp = _make_response(choice="B")

        first = storage.save_response(q, error_resp)
        assert first is not None
        assert first.error == "timeout"

        second = storage.save_response(q, success_resp)
        assert second is not None
        assert second.error is None

        records = _raw_records()
        assert len(records) == 2
        assert records[0]["error"] == "timeout"
        assert records[1]["error"] is None

    def test_success_suppresses_later_duplicates_after_error(self, temp_data_dir: str):
        """Error → success → same success: the third attempt is blocked."""
        q = _make_question()
        error_resp = _make_response(error="timeout", choice=None)
        success_resp = _make_response(choice="B")

        storage.save_response(q, error_resp)
        storage.save_response(q, success_resp)
        third = storage.save_response(q, success_resp)

        assert third is None
        assert len(_raw_records()) == 2  # error + one success

    def test_different_question_hash_not_blocked(self, temp_data_dir: str):
        """Different question → different hash → no dedupe across questions."""
        q1 = _make_question(prompt="A or B?")
        q2 = _make_question(prompt="C or D?")
        resp = _make_response()

        first = storage.save_response(q1, resp)
        second = storage.save_response(q2, resp)

        assert first is not None
        assert second is not None
        assert len(_raw_records()) == 2

    def test_different_model_not_blocked(self, temp_data_dir: str):
        """Same question but different model_id → not a duplicate."""
        q = _make_question()

        first = storage.save_response(q, _make_response(model_id="m1"))
        second = storage.save_response(q, _make_response(model_id="m2"))

        assert first is not None
        assert second is not None
        assert len(_raw_records()) == 2

    def test_different_worldview_not_blocked(self, temp_data_dir: str):
        """Same question but different worldview_id → not a duplicate."""
        q = _make_question()

        first = storage.save_response(q, _make_response(worldview_id="w1"))
        second = storage.save_response(q, _make_response(worldview_id="w2"))

        assert first is not None
        assert second is not None
        assert len(_raw_records()) == 2
