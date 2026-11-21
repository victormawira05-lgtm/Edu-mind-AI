from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.schemas.quiz import GeneratedQuizPayload


class AIProvider(ABC):
    @abstractmethod
    def generate_quiz(
        self,
        *,
        topic: str,
        num_questions: int,
        context_excerpt: Optional[str] = None,
        lecture_title: Optional[str] = None,
    ) -> GeneratedQuizPayload:
        ...

    @abstractmethod
    def generate_answer(self, *, prompt: str, context: str) -> str:
        ...
