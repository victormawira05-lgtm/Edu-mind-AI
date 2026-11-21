from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


READINESS_NOTE = (
    "Readiness metrics reflect graded quiz attempts in your workspace. Topics below the "
    "minimum question threshold are marked as insufficient evidence rather than treated "
    "as demonstrated mastery or weakness, and do not guarantee future exam results."
)


class EvidenceStatus(str, Enum):
    DEMONSTRATED = "demonstrated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class QuizHistoryItem(BaseModel):
    attempt_id: str
    quiz_id: str
    unit_id: Optional[str] = None
    title: str
    score: int = Field(..., ge=0)
    total_questions: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0.0, le=100.0)


class TopicPerformanceItem(BaseModel):
    topic: str
    unit_id: Optional[str] = None
    questions_answered: int = Field(..., ge=0)
    correct_count: int = Field(..., ge=0)
    accuracy_percentage: float = Field(..., ge=0.0, le=100.0)
    evidence_status: EvidenceStatus
    evidence_note: str


class RevisionRecommendation(BaseModel):
    topic: str
    unit_id: Optional[str] = None
    priority: str = Field(..., min_length=1)
    evidence_status: EvidenceStatus
    reason: str = Field(..., min_length=1)
    suggested_action: str = Field(..., min_length=1)
    related_documents: List[str] = Field(default_factory=list)


class ReadinessDashboardResponse(BaseModel):
    user_id: str
    unit_id: Optional[str] = None
    min_evidence_questions: int = Field(..., ge=1)
    total_attempts: int = Field(..., ge=0)
    total_questions_answered: int = Field(..., ge=0)
    total_correct_answers: int = Field(..., ge=0)
    overall_accuracy_percentage: float = Field(..., ge=0.0, le=100.0)
    demonstrated_topics: List[TopicPerformanceItem] = Field(default_factory=list)
    insufficient_evidence_topics: List[TopicPerformanceItem] = Field(default_factory=list)
    recommendations: List[RevisionRecommendation] = Field(default_factory=list)
    recent_attempts: List[QuizHistoryItem] = Field(default_factory=list)
    note: str = Field(default=READINESS_NOTE)
