from __future__ import annotations

from typing import Dict, List
from uuid import uuid4

from backend.schemas.quiz import (
    GeneratedQuizItem,
    GradedQuestionResult,
    QuizAttemptResult,
    QuizSubmitRequest,
)


def grade_quiz_submission(
    *,
    quiz_id: str,
    title: str,
    questions: List[GeneratedQuizItem],
    submission: QuizSubmitRequest,
) -> QuizAttemptResult:
    """
    Deterministically grade a student's quiz submission against the stored answer key.
    AI is never invoked during grading.
    """
    selected_by_qid: Dict[str, int] = {
        ans.question_id: ans.selected_option_index for ans in submission.answers
    }

    graded_items: List[GradedQuestionResult] = []
    correct_count = 0

    for q in questions:
        chosen_idx = selected_by_qid.get(q.id)
        is_correct = (
            chosen_idx is not None
            and 0 <= chosen_idx < len(q.options)
            and chosen_idx == q.correct_option_index
        )
        if is_correct:
            correct_count += 1

        graded_items.append(
            GradedQuestionResult(
                question_id=q.id,
                prompt=q.prompt,
                options=q.options,
                selected_option_index=chosen_idx,
                correct_option_index=q.correct_option_index,
                is_correct=is_correct,
                explanation=q.explanation,
                topic=q.topic,
                lecture_reference=q.lecture_reference,
            )
        )

    total = len(questions)
    percentage = round((correct_count / total) * 100.0, 2) if total > 0 else 0.0

    return QuizAttemptResult(
        attempt_id=str(uuid4()),
        quiz_id=quiz_id,
        title=title,
        score=correct_count,
        total_questions=total,
        percentage=percentage,
        results=graded_items,
    )
