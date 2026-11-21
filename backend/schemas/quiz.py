from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class LectureReference(BaseModel):
    document_title: str = Field(..., min_length=1)
    section_or_page: Optional[str] = None
    excerpt: Optional[str] = None


class GeneratedQuizItem(BaseModel):
    id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=5)
    options: List[str] = Field(..., min_length=2, max_length=6)
    correct_option_index: int = Field(..., ge=0)
    explanation: str = Field(..., min_length=5)
    topic: str = Field(default="General")
    lecture_reference: Optional[LectureReference] = None

    @field_validator("correct_option_index")
    @classmethod
    def validate_index_in_bounds(cls, v: int, info) -> int:
        options = info.data.get("options") or []
        if v >= len(options):
            raise ValueError("correct_option_index must be within options range.")
        return v


class GeneratedQuizPayload(BaseModel):
    title: str = Field(..., min_length=2)
    questions: List[GeneratedQuizItem] = Field(..., min_length=1, max_length=25)


class QuizGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200)
    num_questions: int = Field(default=5, ge=1, le=15)
    unit_id: Optional[str] = None
    context_excerpt: Optional[str] = Field(default=None, max_length=6000)
    lecture_title: Optional[str] = Field(default=None, max_length=200)


class StudentQuizQuestion(BaseModel):
    id: str
    prompt: str
    options: List[str]
    topic: str
    lecture_reference: Optional[LectureReference] = None


class StudentQuizResponse(BaseModel):
    quiz_id: str
    title: str
    unit_id: Optional[str] = None
    questions: List[StudentQuizQuestion]


class QuizAnswerSubmission(BaseModel):
    question_id: str
    selected_option_index: int = Field(..., ge=0)


class QuizSubmitRequest(BaseModel):
    answers: List[QuizAnswerSubmission]


class GradedQuestionResult(BaseModel):
    question_id: str
    prompt: str
    options: List[str]
    selected_option_index: Optional[int]
    correct_option_index: int
    is_correct: bool
    explanation: str
    topic: str
    lecture_reference: Optional[LectureReference] = None


class QuizAttemptResult(BaseModel):
    attempt_id: str
    quiz_id: str
    title: str
    score: int
    total_questions: int
    percentage: float
    results: List[GradedQuestionResult]


class WorkspaceProfilePayload(BaseModel):
    institution: Optional[str] = Field(default=None, max_length=160)
    programme: Optional[str] = Field(default=None, max_length=160)
    semester: Optional[str] = Field(default=None, max_length=80)
    units: List[str] = Field(default_factory=list, max_length=50)
