from __future__ import annotations

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


NON_GUARANTEE_DISCLAIMER = (
    "Historical recurrence reflects only topics and questions observed in your uploaded "
    "past papers and does not guarantee what will appear on future exams."
)


class QuestionType(str, Enum):
    CALCULATION = "calculation"
    CONCEPTUAL = "conceptual"
    PROOF_OR_DERIVATION = "proof_or_derivation"
    SHORT_ANSWER = "short_answer"


class EvidencePointer(BaseModel):
    document_id: str
    document_title: str
    page_number: int = Field(..., ge=1)
    chunk_id: str
    excerpt: str = Field(..., min_length=1)


class LectureLink(BaseModel):
    lecture_document_id: str
    lecture_document_title: str
    page_number: int = Field(..., ge=1)
    chunk_id: str
    relevance_score: float = Field(..., ge=0.0)
    excerpt: str = Field(..., min_length=1)


class ExtractedPastPaperQuestion(BaseModel):
    question_id: str
    unit_id: str
    question_label: str
    question_text: str = Field(..., min_length=3)
    topic: str = Field(..., min_length=1)
    question_type: QuestionType
    source_evidence: EvidencePointer
    lecture_links: List[LectureLink] = Field(default_factory=list)


class TopicRecurrenceEntry(BaseModel):
    topic: str
    occurrence_count: int = Field(..., ge=1)
    paper_count: int = Field(..., ge=1)
    question_types: List[QuestionType] = Field(default_factory=list)
    evidence: List[EvidencePointer] = Field(default_factory=list)
    linked_lectures: List[LectureLink] = Field(default_factory=list)


class PastPaperInsightsResponse(BaseModel):
    unit_id: str
    analyzed_paper_count: int = Field(..., ge=0)
    extracted_questions: List[ExtractedPastPaperQuestion] = Field(default_factory=list)
    recurrence: List[TopicRecurrenceEntry] = Field(default_factory=list)
    disclaimer: str = Field(default=NON_GUARANTEE_DISCLAIMER)
