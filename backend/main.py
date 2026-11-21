from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader

from backend.auth import AuthenticatedUser, get_current_user, verify_owner
from backend.providers.base import AIProvider
from backend.providers.gemini_provider import GeminiProvider
from backend.schemas.quiz import (
    GeneratedQuizPayload,
    QuizAttemptResult,
    QuizGenerateRequest,
    QuizSubmitRequest,
    StudentQuizQuestion,
    StudentQuizResponse,
    WorkspaceProfilePayload,
)
from backend.services.quiz_grader import grade_quiz_submission


@dataclass
class StoredQuizRecord:
    quiz_id: str
    owner_user_id: str
    unit_id: Optional[str]
    payload: GeneratedQuizPayload


@dataclass
class AppStore:
    workspaces: Dict[str, WorkspaceProfilePayload] = field(default_factory=dict)
    quizzes: Dict[str, StoredQuizRecord] = field(default_factory=dict)
    attempts: Dict[str, List[QuizAttemptResult]] = field(default_factory=dict)


app = FastAPI(title="EduMind AI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "templates", "index.html")

STORE = AppStore()
AI_PROVIDER: AIProvider = GeminiProvider()

# Baseline compatibility state for legacy local routes
DOC_TEXT = ""
DOC_NAME = ""
DOC_LINES = []


class LegacyChatRequest(BaseModel):
    question: str = ""


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": 1}


@app.get("/api/workspace", response_model=WorkspaceProfilePayload)
def get_workspace(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WorkspaceProfilePayload:
    return STORE.workspaces.get(current_user.user_id) or WorkspaceProfilePayload()


@app.put("/api/workspace", response_model=WorkspaceProfilePayload)
def upsert_workspace(
    profile: WorkspaceProfilePayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WorkspaceProfilePayload:
    STORE.workspaces[current_user.user_id] = profile
    return profile


@app.post(
    "/api/quizzes/generate",
    response_model=StudentQuizResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_quiz(
    req: QuizGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> StudentQuizResponse:
    try:
        generated = AI_PROVIDER.generate_quiz(
            topic=req.topic.strip(),
            num_questions=req.num_questions,
            context_excerpt=req.context_excerpt,
            lecture_title=req.lecture_title,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate valid structured quiz: {exc}",
        ) from exc

    quiz_id = str(uuid4())
    STORE.quizzes[quiz_id] = StoredQuizRecord(
        quiz_id=quiz_id,
        owner_user_id=current_user.user_id,
        unit_id=req.unit_id,
        payload=generated,
    )

    # Strip correct_option_index before returning quiz to student client
    student_questions = [
        StudentQuizQuestion(
            id=q.id,
            prompt=q.prompt,
            options=q.options,
            topic=q.topic,
            lecture_reference=q.lecture_reference,
        )
        for q in generated.questions
    ]

    return StudentQuizResponse(
        quiz_id=quiz_id,
        title=generated.title,
        unit_id=req.unit_id,
        questions=student_questions,
    )


@app.post("/api/quizzes/{quiz_id}/submit", response_model=QuizAttemptResult)
def submit_quiz(
    quiz_id: str,
    submission: QuizSubmitRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> QuizAttemptResult:
    record = STORE.quizzes.get(quiz_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found.",
        )

    verify_owner(record.owner_user_id, current_user)

    result = grade_quiz_submission(
        quiz_id=record.quiz_id,
        title=record.payload.title,
        questions=record.payload.questions,
        submission=submission,
    )
    STORE.attempts.setdefault(current_user.user_id, []).append(result)
    return result


@app.get("/api/quizzes/{quiz_id}/attempts", response_model=List[QuizAttemptResult])
def list_quiz_attempts(
    quiz_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[QuizAttemptResult]:
    record = STORE.quizzes.get(quiz_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found.",
        )
    verify_owner(record.owner_user_id, current_user)
    user_attempts = STORE.attempts.get(current_user.user_id, [])
    return [a for a in user_attempts if a.quiz_id == quiz_id]


# --- Baseline compatibility endpoints ---
@app.get("/")
def home():
    if os.path.exists(HTML_FILE):
        return FileResponse(HTML_FILE)
    return {"message": "EduMind AI backend running"}


@app.get("/context")
def get_context():
    key_exists = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    return {
        "loaded": bool(DOC_TEXT),
        "filename": DOC_NAME,
        "chars": len(DOC_TEXT),
        "has_key": key_exists,
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global DOC_TEXT, DOC_NAME, DOC_LINES
    reader = PdfReader(file.file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    DOC_TEXT = text
    DOC_LINES = [line for line in text.split("\n") if line.strip()]
    DOC_NAME = file.filename or "uploaded.pdf"
    return {
        "status": "ok",
        "filename": DOC_NAME,
        "pages": len(reader.pages),
        "chars": len(DOC_TEXT),
    }


@app.post("/chat")
async def chat(data: LegacyChatRequest):
    q = data.question.strip()
    if not DOC_TEXT:
        return {"answer": "Please upload PDF first."}
    q_words = [w for w in q.lower().split() if len(w) > 3]
    relevant_lines = []
    char_count = 0
    for line in DOC_LINES:
        if any(w in line.lower() for w in q_words):
            relevant_lines.append(line)
            char_count += len(line) + 1
            if char_count > 3000:
                break
    ctx = "\n".join(relevant_lines) if relevant_lines else DOC_TEXT[:3500]
    return {"answer": AI_PROVIDER.generate_answer(prompt=q, context=ctx)}
