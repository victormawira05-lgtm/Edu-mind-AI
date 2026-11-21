from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.repositories.base import StoredQuizRecord, StudyRepository
from backend.schemas.documents import (
    DocumentCategory,
    DocumentChunkRecord,
    UploadedDocumentSummary,
)
from backend.schemas.past_papers import PastPaperInsightsResponse
from backend.schemas.quiz import (
    GeneratedQuizPayload,
    QuizAttemptResult,
    WorkspaceProfilePayload,
)
from backend.services.readiness_analyzer import AttemptRecordEntry


@dataclass
class InMemoryRepository(StudyRepository):
    workspaces: Dict[str, WorkspaceProfilePayload] = field(default_factory=dict)
    quizzes: Dict[str, StoredQuizRecord] = field(default_factory=dict)
    attempts: Dict[str, List[QuizAttemptResult]] = field(default_factory=dict)
    attempt_entries: List[AttemptRecordEntry] = field(default_factory=list)
    documents: List[UploadedDocumentSummary] = field(default_factory=list)
    chunks: List[DocumentChunkRecord] = field(default_factory=list)
    past_paper_insights: Dict[Tuple[str, str], PastPaperInsightsResponse] = field(
        default_factory=dict
    )

    def clear(self) -> None:
        self.workspaces.clear()
        self.quizzes.clear()
        self.attempts.clear()
        self.attempt_entries.clear()
        self.documents.clear()
        self.chunks.clear()
        self.past_paper_insights.clear()

    def get_workspace(self, user_id: str) -> WorkspaceProfilePayload:
        return self.workspaces.get(user_id) or WorkspaceProfilePayload()

    def upsert_workspace(
        self, user_id: str, profile: WorkspaceProfilePayload
    ) -> WorkspaceProfilePayload:
        self.workspaces[user_id] = profile
        return profile

    def save_document_with_chunks(
        self,
        user_id: str,
        summary: UploadedDocumentSummary,
        chunks: List[DocumentChunkRecord],
    ) -> UploadedDocumentSummary:
        owned_summary = summary.model_copy(update={"user_id": user_id})
        owned_chunks = [c.model_copy(update={"user_id": user_id}) for c in chunks]
        self.documents.append(owned_summary)
        self.chunks.extend(owned_chunks)
        return owned_summary

    def list_documents(
        self, user_id: str, unit_id: str
    ) -> List[UploadedDocumentSummary]:
        norm_unit = unit_id.strip() or "general"
        return [
            d
            for d in self.documents
            if d.user_id == user_id and d.unit_id == norm_unit
        ]

    def list_chunks(
        self,
        user_id: str,
        unit_id: str,
        category: Optional[DocumentCategory] = None,
    ) -> List[DocumentChunkRecord]:
        norm_unit = unit_id.strip() or "general"
        return [
            c
            for c in self.chunks
            if c.user_id == user_id
            and c.unit_id == norm_unit
            and (category is None or c.category == category)
        ]

    def save_quiz(
        self,
        user_id: str,
        quiz_id: str,
        unit_id: Optional[str],
        payload: GeneratedQuizPayload,
    ) -> StoredQuizRecord:
        norm_unit = unit_id.strip() if unit_id and unit_id.strip() else None
        record = StoredQuizRecord(
            quiz_id=quiz_id,
            owner_user_id=user_id,
            unit_id=norm_unit,
            payload=payload,
        )
        self.quizzes[quiz_id] = record
        return record

    def get_quiz(self, quiz_id: str) -> Optional[StoredQuizRecord]:
        return self.quizzes.get(quiz_id)

    def record_attempt(
        self,
        user_id: str,
        unit_id: Optional[str],
        result: QuizAttemptResult,
    ) -> None:
        norm_unit = unit_id.strip() if unit_id and unit_id.strip() else None
        self.attempts.setdefault(user_id, []).append(result)
        self.attempt_entries.append(
            AttemptRecordEntry(
                user_id=user_id,
                unit_id=norm_unit,
                result=result,
            )
        )

    def list_attempt_entries(
        self, user_id: str, unit_id: Optional[str] = None
    ) -> List[AttemptRecordEntry]:
        norm_unit = unit_id.strip() if unit_id and unit_id.strip() else None
        return [
            e
            for e in self.attempt_entries
            if e.user_id == user_id and (norm_unit is None or e.unit_id == norm_unit)
        ]

    def save_past_paper_insights(
        self, user_id: str, unit_id: str, insights: PastPaperInsightsResponse
    ) -> None:
        norm_unit = unit_id.strip() or "general"
        self.past_paper_insights[(user_id, norm_unit)] = insights

    def get_saved_past_paper_insights(
        self, user_id: str, unit_id: str
    ) -> Optional[PastPaperInsightsResponse]:
        norm_unit = unit_id.strip() or "general"
        return self.past_paper_insights.get((user_id, norm_unit))
