import csv
import io
import json
import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from config import MODELS, WORLDVIEWS
from llm_service import ask_slots, generate_question_image
from models import (
    AskRequest,
    AskResponse,
    ImageOperationResult,
    ModelInfo,
    Question,
    QuestionCreate,
    QuestionUpdate,
    StoredResponse,
    Worldview,
)
import storage

QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "questions.json")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "data", "images")

app = FastAPI(title="Trolley Problem LLM Comparison")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_questions: list[Question] = []


def _image_path(question_id: int) -> str:
    return os.path.join(IMAGES_DIR, f"{question_id}.img")


def _detect_media_type(data: bytes) -> str:
    if data[:2] == b'\xff\xd8':
        return 'image/jpeg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return 'image/octet-stream'


def _validate_model_id(model_id: str) -> None:
    known = {m["model_id"] for m in MODELS}
    if model_id not in known:
        raise HTTPException(status_code=422, detail=f"Unknown model_id: {model_id}")


def _validate_worldview_id(worldview_id: str) -> None:
    known = {w["id"] for w in WORLDVIEWS}
    if worldview_id not in known:
        raise HTTPException(status_code=422, detail=f"Unknown worldview_id: {worldview_id}")


def _validate_question_row(row: dict, index: int) -> list[str]:
    """Validate a single upload question row. Returns list of error messages (empty = valid)."""
    errors: list[str] = []
    # id
    if "id" not in row:
        errors.append("missing 'id'")
    else:
        try:
            int(row["id"])
        except (ValueError, TypeError):
            errors.append(f"invalid 'id': {row['id']!r}")
    # title
    title = row.get("title")
    if not title or not str(title).strip():
        errors.append("'title' must not be blank")
    # prompt
    prompt = row.get("prompt")
    if not prompt or not str(prompt).strip():
        errors.append("'prompt' must not be blank")
    # options
    options = row.get("options")
    if not isinstance(options, list):
        errors.append("'options' must be a list")
    elif len(options) < 2:
        errors.append("at least 2 options required")
    else:
        stripped = [str(o).strip() for o in options]
        if any(not o for o in stripped):
            errors.append("option text must not be blank")
        elif len(set(stripped)) != len(stripped):
            errors.append("duplicate option values are not allowed")
    return errors


def _load_questions_from_file(path: str) -> list[Question]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Question(**q) for q in data]


def _save_questions_to_file(path: str, questions: list[Question]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([q.model_dump() for q in questions], f, indent=2, ensure_ascii=False)


def _parse_questions_csv(content: str) -> list[Question]:
    reader = csv.DictReader(io.StringIO(content))
    questions = []
    for row in reader:
        options = [o.strip() for o in row["options"].split(";")]
        questions.append(
            Question(
                id=int(row["id"]),
                title=row["title"],
                prompt=row["prompt"],
                options=options,
            )
        )
    return questions


@app.on_event("startup")
def startup_event():
    global _questions
    _questions = _load_questions_from_file(QUESTIONS_FILE)


@app.get("/api/questions", response_model=list[Question])
def get_questions():
    return _questions


@app.post("/api/questions", response_model=Question, status_code=201)
def create_question(body: QuestionCreate):
    global _questions
    new_id = max((q.id for q in _questions), default=0) + 1
    question = Question(id=new_id, title=body.title, prompt=body.prompt, options=body.options)
    _questions.append(question)
    _save_questions_to_file(QUESTIONS_FILE, _questions)
    return question


@app.put("/api/questions/{question_id}", response_model=Question)
def update_question(question_id: int, body: QuestionUpdate):
    for i, q in enumerate(_questions):
        if q.id == question_id:
            updated = q.model_copy(update={k: v for k, v in body.model_dump().items() if v is not None})
            _questions[i] = updated
            _save_questions_to_file(QUESTIONS_FILE, _questions)
            return updated
    raise HTTPException(status_code=404, detail="Question not found")


@app.delete("/api/questions/{question_id}", status_code=204)
def delete_question(question_id: int):
    global _questions
    before = len(_questions)
    _questions = [q for q in _questions if q.id != question_id]
    if len(_questions) == before:
        raise HTTPException(status_code=404, detail="Question not found")
    _save_questions_to_file(QUESTIONS_FILE, _questions)
    cached = _image_path(question_id)
    if os.path.exists(cached):
        os.remove(cached)


@app.get("/api/questions/{question_id}/image")
def get_question_image(question_id: int):
    question = next((q for q in _questions if q.id == question_id), None)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    path = _image_path(question_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No cached image for this question")
    with open(path, "rb") as f:
        image_bytes = f.read()
    return Response(content=image_bytes, media_type=_detect_media_type(image_bytes))


@app.post("/api/questions/{question_id}/image", response_model=ImageOperationResult)
async def post_question_image(question_id: int):
    question = next((q for q in _questions if q.id == question_id), None)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        image_bytes = await generate_question_image(question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    path = _image_path(question_id)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return ImageOperationResult(
        question_id=question_id,
        cached=True,
        media_type=_detect_media_type(image_bytes),
    )


@app.delete("/api/questions/{question_id}/image", status_code=204)
def delete_question_image(question_id: int):
    if not any(q.id == question_id for q in _questions):
        raise HTTPException(status_code=404, detail="Question not found")
    path = _image_path(question_id)
    if os.path.exists(path):
        os.remove(path)


@app.get("/api/models", response_model=list[ModelInfo])
def get_models():
    return [ModelInfo(**m) for m in MODELS]


@app.get("/api/worldviews", response_model=list[Worldview])
def get_worldviews():
    return [Worldview(**w) for w in WORLDVIEWS]


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    question = next((q for q in _questions if q.id == request.question_id), None)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # Catalog validation before any LLM call
    for slot in request.slots:
        _validate_model_id(slot.model_id)
        _validate_worldview_id(slot.worldview_id)

    responses = await ask_slots(question, request.slots)
    for resp in responses:
        storage.save_response(question, resp)

    return AskResponse(question_id=question.id, responses=responses)


@app.get("/api/responses", response_model=list[StoredResponse])
def get_responses():
    return storage.get_all_responses()


@app.get("/api/export")
def export(format: str = "json"):
    if format == "csv":
        content = storage.export_csv()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=responses.csv"},
        )
    content = storage.export_json()
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=responses.json"},
    )


@app.post("/api/questions/upload", response_model=list[Question])
async def upload_questions(file: UploadFile = File(...)):
    global _questions
    content = (await file.read()).decode("utf-8")
    filename = file.filename or ""

    # Parse into raw dicts first
    try:
        if filename.endswith(".csv"):
            rows: list[dict] = list(csv.DictReader(io.StringIO(content)))
            for row in rows:
                row["options"] = [o.strip() for o in row["options"].split(";")]
        else:
            rows = json.loads(content)
            if not isinstance(rows, list):
                raise HTTPException(status_code=422, detail="JSON payload must be an array")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {exc}")

    # Atomic validation: validate ALL rows before any mutation
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Row {i} is not an object: {row!r}",
            )
        row_errors = _validate_question_row(row, i)
        if row_errors:
            raise HTTPException(
                status_code=422,
                detail=f"Row {i} invalid: {'; '.join(row_errors)}",
            )

    # All rows valid — create Question objects and save
    try:
        parsed = [Question(**row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Question construction failed: {exc}")

    _questions = parsed
    _save_questions_to_file(QUESTIONS_FILE, _questions)
    return _questions
