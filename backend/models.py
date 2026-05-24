from pydantic import BaseModel, field_validator
from typing import Optional


def _validate_options(v: object) -> list[str]:
    """Shared option-list validation: >=2 items, no blanks, no duplicates."""
    if not isinstance(v, list):
        raise ValueError("must be a list")
    if len(v) < 2:
        raise ValueError("at least 2 options required")
    stripped = [o.strip() if isinstance(o, str) else str(o) for o in v]
    if any(not o for o in stripped):
        raise ValueError("option text must not be blank")
    if len(set(stripped)) != len(stripped):
        raise ValueError("duplicate option values are not allowed")
    return v  # type: ignore[return-value]


class Question(BaseModel):
    id: int
    title: str
    prompt: str
    options: list[str]


class QuestionCreate(BaseModel):
    title: str
    prompt: str
    options: list[str]

    @field_validator("title", "prompt")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v

    @field_validator("options")
    @classmethod
    def valid_options(cls, v: list[str]) -> list[str]:
        return _validate_options(v)  # type: ignore[return-value]


class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    options: Optional[list[str]] = None

    @field_validator("title", "prompt")
    @classmethod
    def not_blank_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError("must not be blank")
        return v

    @field_validator("options")
    @classmethod
    def valid_options_if_provided(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        return _validate_options(v)  # type: ignore[return-value]


class ModelInfo(BaseModel):
    model_id: str
    display_name: str


class Worldview(BaseModel):
    id: str
    label: str
    system_prompt: str


class Slot(BaseModel):
    slot_id: str
    model_id: str
    worldview_id: str


class ModelResponse(BaseModel):
    slot_id: str
    model_id: str
    display_name: str
    worldview_id: str
    worldview_label: str
    choice: Optional[str] = None
    reasoning: Optional[str] = None
    moral_framework: Optional[str] = None
    error: Optional[str] = None


class AskRequest(BaseModel):
    question_id: int
    slots: list[Slot]


class AskResponse(BaseModel):
    question_id: int
    responses: list[ModelResponse]


class StoredResponse(BaseModel):
    question_id: int
    question_hash: Optional[str] = None
    question_title: Optional[str] = None
    question_prompt: Optional[str] = None
    question_options: Optional[list[str]] = None
    slot_id: str
    model_id: str
    display_name: str
    worldview_id: str
    worldview_label: str
    choice: Optional[str] = None
    reasoning: Optional[str] = None
    moral_framework: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


class ImageOperationResult(BaseModel):
    question_id: int
    cached: bool
    media_type: str
