from fastapi.testclient import TestClient

from backend import main as backend_main
from backend.schemas.documents import (
    DocumentCategory,
    DocumentChunkRecord,
    UploadedDocumentSummary,
)


def setup_function():
    backend_main.STORE.workspaces.clear()
    backend_main.STORE.quizzes.clear()
    backend_main.STORE.attempts.clear()
    backend_main.STORE.documents.clear()
    backend_main.STORE.chunks.clear()


def _seed_unit_materials(user_id: str = "student-1", unit_id: str = "STA212"):
    backend_main.STORE.documents.extend(
        [
            UploadedDocumentSummary(
                document_id="doc-lec-1",
                user_id=user_id,
                unit_id=unit_id,
                title="Probability Lecture Notes",
                filename="prob_notes.pdf",
                category=DocumentCategory.LECTURE_NOTES,
                page_count=4,
                extracted_chars=500,
                chunk_count=2,
            ),
            UploadedDocumentSummary(
                document_id="doc-pp-1",
                user_id=user_id,
                unit_id=unit_id,
                title="2024 Past Exam",
                filename="exam_2024.pdf",
                category=DocumentCategory.PAST_PAPER,
                page_count=2,
                extracted_chars=300,
                chunk_count=1,
            ),
            UploadedDocumentSummary(
                document_id="doc-pp-2",
                user_id=user_id,
                unit_id=unit_id,
                title="2025 Past Exam",
                filename="exam_2025.pdf",
                category=DocumentCategory.PAST_PAPER,
                page_count=2,
                extracted_chars=300,
                chunk_count=1,
            ),
        ]
    )

    backend_main.STORE.chunks.extend(
        [
            DocumentChunkRecord(
                chunk_id="doc-lec-1-c0",
                user_id=user_id,
                unit_id=unit_id,
                document_id="doc-lec-1",
                document_title="Probability Lecture Notes",
                category=DocumentCategory.LECTURE_NOTES,
                page_number=3,
                chunk_index=0,
                content=(
                    "Bayes theorem updates conditional probability given new evidence "
                    "and prior distributions."
                ),
            ),
            DocumentChunkRecord(
                chunk_id="doc-pp-1-c0",
                user_id=user_id,
                unit_id=unit_id,
                document_id="doc-pp-1",
                document_title="2024 Past Exam",
                category=DocumentCategory.PAST_PAPER,
                page_number=1,
                chunk_index=0,
                content=(
                    "Question 1: Calculate the conditional probability using Bayes theorem "
                    "given the prior distribution."
                ),
            ),
            DocumentChunkRecord(
                chunk_id="doc-pp-2-c0",
                user_id=user_id,
                unit_id=unit_id,
                document_id="doc-pp-2",
                document_title="2025 Past Exam",
                category=DocumentCategory.PAST_PAPER,
                page_number=2,
                chunk_index=0,
                content=(
                    "Question 2: Define conditional probability and explain Bayes theorem "
                    "with new evidence."
                ),
            ),
        ]
    )


def test_past_paper_extraction_recurrence_evidence_and_disclaimer(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH_BYPASS", "true")
    _seed_unit_materials(user_id="student-1", unit_id="STA212")

    client = TestClient(backend_main.app)
    res = client.post(
        "/api/units/STA212/past-papers/analyze",
        headers={"X-Dev-User-Id": "student-1"},
    )
    assert res.status_code == 200
    body = res.json()

    assert body["analyzed_paper_count"] == 2
    assert len(body["extracted_questions"]) == 2
    assert "does not guarantee" in body["disclaimer"].lower()

    # Every extracted question carries verifiable source evidence
    for q in body["extracted_questions"]:
        ev = q["source_evidence"]
        assert ev["document_title"]
        assert ev["page_number"] >= 1
        assert ev["chunk_id"]
        assert ev["excerpt"]

    # Recurrence entries include evidence pointers and linked lecture notes
    assert len(body["recurrence"]) >= 1
    top_rec = body["recurrence"][0]
    assert top_rec["occurrence_count"] == 2
    assert top_rec["paper_count"] == 2
    assert len(top_rec["evidence"]) == 2
    assert len(top_rec["linked_lectures"]) >= 1
    assert top_rec["linked_lectures"][0]["lecture_document_title"] == "Probability Lecture Notes"
    assert top_rec["linked_lectures"][0]["page_number"] == 3


def test_past_paper_insights_isolated_by_user(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH_BYPASS", "true")
    _seed_unit_materials(user_id="student-1", unit_id="STA212")

    client = TestClient(backend_main.app)
    res = client.post(
        "/api/units/STA212/past-papers/analyze",
        headers={"X-Dev-User-Id": "student-2"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["analyzed_paper_count"] == 0
    assert body["extracted_questions"] == []
    assert body["recurrence"] == []
