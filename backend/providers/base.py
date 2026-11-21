from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.schemas.quiz import GeneratedQuizPayload


class AIProvider(ABC):
    """Provider-agnostic interface so AI backends (Gemini first) can be swapped cleanly."""

    @abstractmethod
    def generate_quiz(
        self,
        *,
        topic: str,
        num_questions: int,
        context_excerpt: Optional[str] = None,
        lecture_title: Optional[str] = None,
    ) -> GeneratedQuizPayload:
        """Generate and return a schema-validated GeneratedQuizPayload."""

    @abstractmethod
    def generate_answer(self, *, prompt: str, context: str) -> str:
        """Generate a tutor response for study/Q&A workflows."""
