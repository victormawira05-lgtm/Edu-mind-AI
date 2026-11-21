from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

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
class StoredQuizRecord:
    quiz_id: str
    owner_user_id: str
    unit_id: Optional[str]
    payload: GeneratedQuizPayload


class StudyRepository(ABC):
    # Workspace (P1)
    @abstractmethod
    def get_workspace(self, user_id: str) -> WorkspaceProfilePayload: ...

    @abstractmethod
    def upsert_workspace(
        self, user_id: str, profile: WorkspaceProfilePayload
    ) -> WorkspaceProfilePayload: ...

    # Documents & Chunks (P2)
    @abstractmethod
    def save_document_with_chunks(
        self,
        user_id: str,
        summary: UploadedDocumentSummary,
        chunks: List[DocumentChunkRecord],
    ) -> UploadedDocumentSummary: ...

    @abstractmethod
    def list_documents(
        self, user_id: str, unit_id: str
    ) -> List[UploadedDocumentSummary]: ...

    @abstractmethod
    def list_chunks(
        self,
        user_id: str,
        unit_id: str,
        category: Optional[DocumentCategory] = None,
    ) -> List[DocumentChunkRecord]: ...

    # Quizzes & Attempts (P1 & P4)
    @abstractmethod
    def save_quiz(
        self,
        user_id: str,
        quiz_id: str,
        unit_id: Optional[str],
        payload: GeneratedQuizPayload,
    ) -> StoredQuizRecord: ...

    @abstractmethod
    def get_quiz(self, quiz_id: str) -> Optional[StoredQuizRecord]: ...

    @abstractmethod
    def record_attempt(
        self,
        user_id: str,
        unit_id: Optional[str],
        result: QuizAttemptResult,
    ) -> None: ...

    @abstractmethod
    def list_attempt_entries(
        self, user_id: str, unit_id: Optional[str] = None
    ) -> List[AttemptRecordEntry]: ...

    # Past-Paper Insights (P3)
    @abstractmethod
    def save_past_paper_insights(
        self, user_id: str, unit_id: str, insights: PastPaperInsightsResponse
    ) -> None: ...

    @abstractmethod
    def get_saved_past_paper_insights(
        self, user_id: str, unit_id: str
    ) -> Optional[PastPaperInsightsResponse]: ...
