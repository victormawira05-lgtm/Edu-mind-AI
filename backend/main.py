from __future__ import annotations

from backend.cors_config import get_allowed_origins

import os
from typing import List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader

from backend.auth import AuthenticatedUser, get_current_user, verify_owner
from backend.providers.base import AIProvider
from backend.providers.gemini_provider import GeminiProvider
from backend.repositories.base import StudyRepository
from backend.repositories.memory_repo import InMemoryRepository
from backend.repositories.postgres_repo import PostgresRepository
from backend.schemas.documents import (
    DocumentCategory,
    RetrieveRequest,
    RetrieveResponse,
    ScannedPdfErrorDetail,
    UploadedDocumentSummary,
)
from backend.schemas.past_papers import PastPaperInsightsResponse
from backend.schemas.quiz import (
    QuizAttemptResult,
    QuizGenerateRequest,
    QuizSubmitRequest,
    StudentQuizQuestion,
    StudentQuizResponse,
    WorkspaceProfilePayload,
)
from backend.schemas.readiness import QuizHistoryItem, ReadinessDashboardResponse
from backend.services.past_paper_analyzer import analyze_unit_past_papers
from backend.services.pdf_ingestion import (
    ScannedPdfUnsupportedError,
    ingest_pdf_document,
)
from backend.services.quiz_grader import grade_quiz_submission
from backend.services.readiness_analyzer import build_readiness_dashboard
from backend.services.retriever import retrieve_chunks_from_records


def create_default_repository() -> StudyRepository:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if database_url:
        return PostgresRepository(database_url=database_url)
    return InMemoryRepository()


app = FastAPI(title="EduMind AI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "templates", "index.html")

REPO: StudyRepository = create_default_repository()
STORE = REPO
AI_PROVIDER: AIProvider = GeminiProvider()

DOC_TEXT = ""
DOC_NAME = ""
DOC_LINES = []


class LegacyChatRequest(BaseModel):
    question: str = ""


@app.get("/health")
def health() -> dict:
    backend_mode = "postgres" if isinstance(REPO, PostgresRepository) else "memory"
    return {"status": "ok", "phase": 4, "storage": backend_mode}


@app.get("/api/workspace", response_model=WorkspaceProfilePayload)
def get_workspace(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WorkspaceProfilePayload:
    return REPO.get_workspace(current_user.user_id)


@app.put("/api/workspace", response_model=WorkspaceProfilePayload)
def upsert_workspace(
    profile: WorkspaceProfilePayload,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WorkspaceProfilePayload:
    return REPO.upsert_workspace(current_user.user_id, profile)


@app.post(
    "/api/units/{unit_id}/documents",
    response_model=UploadedDocumentSummary,
    status_code=status.HTTP_201_CREATED,
)
async def upload_unit_document(
    unit_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    category: DocumentCategory = Form(default=DocumentCategory.LECTURE_NOTES),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UploadedDocumentSummary:
    normalized_unit = unit_id.strip() or "general"
    filename = file.filename or "document.pdf"
    doc_title = (title or "").strip() or filename

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are currently supported.",
        )

    pdf_bytes = await file.read()
    try:
        doc_id, page_count, total_chars, chunk_records = ingest_pdf_document(
            pdf_bytes=pdf_bytes,
            filename=filename,
            title=doc_title,
            category=category,
            unit_id=normalized_unit,
            user_id=current_user.user_id,
        )
    except ScannedPdfUnsupportedError as exc:
        detail = ScannedPdfErrorDetail(
            filename=exc.filename,
            page_count=exc.page_count,
            message=exc.message,
        ).model_dump()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        ) from exc

    summary = UploadedDocumentSummary(
        document_id=doc_id,
        user_id=current_user.user_id,
        unit_id=normalized_unit,
        title=doc_title,
        filename=filename,
        category=category,
        page_count=page_count,
        extracted_chars=total_chars,
        chunk_count=len(chunk_records),
    )
    return REPO.save_document_with_chunks(
        user_id=current_user.user_id,
        summary=summary,
        chunks=chunk_records,
    )


@app.get(
    "/api/units/{unit_id}/documents",
    response_model=List[UploadedDocumentSummary],
)
def list_unit_documents(
    unit_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[UploadedDocumentSummary]:
    normalized_unit = unit_id.strip() or "general"
    return REPO.list_documents(user_id=current_user.user_id, unit_id=normalized_unit)


@app.post(
    "/api/units/{unit_id}/retrieve",
    response_model=RetrieveResponse,
)
def retrieve_unit_chunks(
    unit_id: str,
    req: RetrieveRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RetrieveResponse:
    normalized_unit = unit_id.strip() or "general"
    scoped_chunks = REPO.list_chunks(
        user_id=current_user.user_id,
        unit_id=normalized_unit,
        category=req.category,
    )
    matches = retrieve_chunks_from_records(
        scoped_chunks,
        user_id=current_user.user_id,
        unit_id=normalized_unit,
        query=req.query,
        top_k=req.top_k,
        category=req.category,
    )
    return RetrieveResponse(
        unit_id=normalized_unit,
        query=req.query,
        results=matches,
    )


@app.post(
    "/api/units/{unit_id}/past-papers/analyze",
    response_model=PastPaperInsightsResponse,
)
def analyze_past_papers_endpoint(
    unit_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PastPaperInsightsResponse:
    normalized_unit = unit_id.strip() or "general"
    scoped_chunks = REPO.list_chunks(
        user_id=current_user.user_id,
        unit_id=normalized_unit,
    )
    insights = analyze_unit_past_papers(
        scoped_chunks,
        user_id=current_user.user_id,
        unit_id=normalized_unit,
    )
    REPO.save_past_paper_insights(
        user_id=current_user.user_id,
        unit_id=normalized_unit,
        insights=insights,
    )
    return insights


@app.get(
    "/api/units/{unit_id}/past-papers/insights",
    response_model=PastPaperInsightsResponse,
)
def get_past_paper_insights_endpoint(
    unit_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PastPaperInsightsResponse:
    normalized_unit = unit_id.strip() or "general"
    saved = REPO.get_saved_past_paper_insights(
        user_id=current_user.user_id,
        unit_id=normalized_unit,
    )
    if saved is not None:
        return saved
    scoped_chunks = REPO.list_chunks(
        user_id=current_user.user_id,
        unit_id=normalized_unit,
    )
    return analyze_unit_past_papers(
        scoped_chunks,
        user_id=current_user.user_id,
        unit_id=normalized_unit,
    )


@app.post(
    "/api/quizzes/generate",
    response_model=StudentQuizResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_quiz(
    req: QuizGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> StudentQuizResponse:
    context_excerpt = req.context_excerpt
    lecture_title = req.lecture_title

    if not context_excerpt and req.unit_id:
        scoped_chunks = REPO.list_chunks(
            user_id=current_user.user_id,
            unit_id=req.unit_id,
        )
        retrieved = retrieve_chunks_from_records(
            scoped_chunks,
            user_id=current_user.user_id,
            unit_id=req.unit_id,
            query=req.topic,
            top_k=3,
        )
        if retrieved:
            context_excerpt = "\n\n".join(item.content for item in retrieved)
            lecture_title = lecture_title or retrieved[0].source.document_title

    try:
        generated = AI_PROVIDER.generate_quiz(
            topic=req.topic.strip(),
            num_questions=req.num_questions,
            context_excerpt=context_excerpt,
            lecture_title=lecture_title,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate valid structured quiz: {exc}",
        ) from exc

    quiz_id = str(uuid4())
    REPO.save_quiz(
        user_id=current_user.user_id,
        quiz_id=quiz_id,
        unit_id=req.unit_id,
        payload=generated,
    )

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
    record = REPO.get_quiz(quiz_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_owner(record.owner_user_id, current_user)
    result = grade_quiz_submission(
        quiz_id=record.quiz_id,
        title=record.payload.title,
        questions=record.payload.questions,
        submission=submission,
    )
    REPO.record_attempt(
        user_id=current_user.user_id,
        unit_id=record.unit_id,
        result=result,
    )
    return result


@app.get("/api/quizzes/history", response_model=List[QuizHistoryItem])
def get_quiz_history(
    unit_id: Optional[str] = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[QuizHistoryItem]:
    entries = REPO.list_attempt_entries(user_id=current_user.user_id, unit_id=unit_id)
    dashboard = build_readiness_dashboard(
        entries,
        user_id=current_user.user_id,
        unit_id=unit_id,
    )
    return dashboard.recent_attempts


@app.get("/api/readiness", response_model=ReadinessDashboardResponse)
def get_readiness_dashboard(
    unit_id: Optional[str] = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ReadinessDashboardResponse:
    entries = REPO.list_attempt_entries(user_id=current_user.user_id, unit_id=unit_id)
    unit_chunks = REPO.list_chunks(user_id=current_user.user_id, unit_id=unit_id or "general")
    return build_readiness_dashboard(
        entries,
        user_id=current_user.user_id,
        unit_id=unit_id,
        chunks=unit_chunks,
    )


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


def _chunk_text_for_summary(text: str, chunk_size: int = 25000, max_chunks: int = 12) -> List[str]:
    cleaned = text.strip()
    if len(cleaned) <= 60000:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    length = len(cleaned)
    while start < length and len(chunks) < max_chunks:
        end = min(start + chunk_size, length)
        if end < length:
            newline_break = cleaned.rfind("\n", start + int(chunk_size * 0.7), end)
            if newline_break > start:
                end = newline_break
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end
    return chunks


def _summarize_document_sections(question: str, doc_text: str, doc_name: str) -> str:
    if len(doc_text) <= 60000:
        prompt_to_use = (
            f"{question}\n\nProvide a comprehensive, structured summary covering every major section, "
            f"concept, architecture, and key takeaway from '{doc_name}'."
        )
        return AI_PROVIDER.generate_answer(prompt=prompt_to_use, context=doc_text)

    chunks = _chunk_text_for_summary(doc_text)
    total_parts = len(chunks)
    section_summaries: List[str] = []

    for idx, chunk in enumerate(chunks, start=1):
        part_prompt = (
            f"Summarize Part {idx} of {total_parts} of '{doc_name}' for the request: '{question}'. "
            "Extract key headings, definitions, architectures, formulas/metrics, and main points concisely."
        )
        part_summary = AI_PROVIDER.generate_answer(prompt=part_prompt, context=chunk)
        section_summaries.append(f"### Part {idx} of {total_parts}\n{part_summary}")

    combined_sections = "\n\n".join(section_summaries)
    synth_prompt = (
        f"{question}\n\nCombine these {total_parts} section summaries of '{doc_name}' into a clear, "
        "well-structured full-document summary with major sections/themes and key takeaways, "
        "without dropping important details."
    )
    return AI_PROVIDER.generate_answer(prompt=synth_prompt, context=combined_sections)


@app.post("/chat")
async def chat(data: LegacyChatRequest):
    q = data.question.strip()
    if not DOC_TEXT:
        return {"answer": "Please upload PDF first."}
    is_whole_summary = any(phrase in q.lower() for phrase in ("summarize", "summary", "whole pdf", "entire document", "whole document"))
    if is_whole_summary:
        answer = _summarize_document_sections(question=q, doc_text=DOC_TEXT, doc_name=DOC_NAME or "uploaded.pdf")
        return {"answer": answer}

    q_words = [w for w in q.lower().split() if len(w) > 3]
    relevant_lines = []
    char_count = 0
    for line in DOC_LINES:
        if any(w in line.lower() for w in q_words):
            relevant_lines.append(line)
            char_count += len(line) + 1
            if char_count > 12000:
                break
    ctx = "\n".join(relevant_lines) if relevant_lines else DOC_TEXT[:60000]
    return {"answer": AI_PROVIDER.generate_answer(prompt=q, context=ctx)}

