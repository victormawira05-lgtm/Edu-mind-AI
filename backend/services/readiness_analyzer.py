from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from backend.schemas.documents import DocumentChunkRecord
from backend.schemas.quiz import QuizAttemptResult
from backend.schemas.readiness import (
    EvidenceStatus,
    QuizHistoryItem,
    READINESS_NOTE,
    ReadinessDashboardResponse,
    RevisionRecommendation,
    TopicPerformanceItem,
)

MIN_EVIDENCE_QUESTIONS = 3


@dataclass
class AttemptRecordEntry:
    user_id: str
    unit_id: Optional[str]
    result: QuizAttemptResult


def _find_related_doc_titles(
    chunks: Iterable[DocumentChunkRecord],
    *,
    user_id: str,
    unit_id: Optional[str],
    topic: str,
    limit: int = 2,
) -> List[str]:
    topic_words = [w.lower() for w in topic.split() if len(w) > 3]
    seen: List[str] = []
    for ch in chunks:
        if ch.user_id != user_id:
            continue
        if unit_id and ch.unit_id != unit_id:
            continue
        haystack = f"{ch.document_title} {ch.content}".lower()
        if any(w in haystack for w in topic_words) and ch.document_title not in seen:
            seen.append(ch.document_title)
            if len(seen) >= limit:
                break
    return seen


def build_readiness_dashboard(
    entries: Iterable[AttemptRecordEntry],
    *,
    user_id: str,
    unit_id: Optional[str] = None,
    chunks: Iterable[DocumentChunkRecord] = (),
    min_evidence_questions: int = MIN_EVIDENCE_QUESTIONS,
) -> ReadinessDashboardResponse:
    scoped: List[AttemptRecordEntry] = [
        e
        for e in entries
        if e.user_id == user_id and (unit_id is None or e.unit_id == unit_id)
    ]

    topic_stats: Dict[Tuple[str, Optional[str]], List[int]] = {}
    recent_attempts: List[QuizHistoryItem] = []

    total_questions_answered = 0
    total_correct_answers = 0

    for entry in scoped:
        res = entry.result
        recent_attempts.append(
            QuizHistoryItem(
                attempt_id=res.attempt_id,
                quiz_id=res.quiz_id,
                unit_id=entry.unit_id,
                title=res.title,
                score=res.score,
                total_questions=res.total_questions,
                percentage=res.percentage,
            )
        )
        for q in res.results:
            total_questions_answered += 1
            if q.is_correct:
                total_correct_answers += 1
            key = (q.topic.strip() or "General", entry.unit_id)
            if key not in topic_stats:
                topic_stats[key] = [0, 0]
            topic_stats[key][0] += 1
            if q.is_correct:
                topic_stats[key][1] += 1

    overall_accuracy = (
        round((total_correct_answers / total_questions_answered) * 100.0, 2)
        if total_questions_answered > 0
        else 0.0
    )

    demonstrated_topics: List[TopicPerformanceItem] = []
    insufficient_evidence_topics: List[TopicPerformanceItem] = []
    recommendations: List[RevisionRecommendation] = []

    for (t_name, t_unit), (answered, correct) in sorted(
        topic_stats.items(), key=lambda item: item[0][0].lower()
    ):
        acc = round((correct / answered) * 100.0, 2) if answered > 0 else 0.0
        has_enough = answered >= min_evidence_questions
        status_val = (
            EvidenceStatus.DEMONSTRATED if has_enough else EvidenceStatus.INSUFFICIENT_EVIDENCE
        )
        note_val = (
            f"Demonstrated across {answered} answered questions ({correct}/{answered} correct)."
            if has_enough
            else (
                f"Insufficient evidence: only {answered} of {min_evidence_questions} "
                f"minimum questions answered."
            )
        )
        perf_item = TopicPerformanceItem(
            topic=t_name,
            unit_id=t_unit,
            questions_answered=answered,
            correct_count=correct,
            accuracy_percentage=acc,
            evidence_status=status_val,
            evidence_note=note_val,
        )

        related_docs = _find_related_doc_titles(
            chunks, user_id=user_id, unit_id=t_unit, topic=t_name
        )

        if has_enough:
            demonstrated_topics.append(perf_item)
            if acc < 70.0:
                recommendations.append(
                    RevisionRecommendation(
                        topic=t_name,
                        unit_id=t_unit,
                        priority="high",
                        evidence_status=EvidenceStatus.DEMONSTRATED,
                        reason=(
                            f"Demonstrated accuracy is {acc}% across {answered} questions "
                            f"({correct}/{answered} correct)."
                        ),
                        suggested_action=(
                            f"Review core concepts and generate a targeted practice quiz on {t_name}."
                        ),
                        related_documents=related_docs,
                    )
                )
        else:
            insufficient_evidence_topics.append(perf_item)
            recommendations.append(
                RevisionRecommendation(
                    topic=t_name,
                    unit_id=t_unit,
                    priority="moderate",
                    evidence_status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                    reason=(
                        f"Only {answered} question(s) answered so far (minimum {min_evidence_questions} "
                        f"needed for demonstrated performance)."
                    ),
                    suggested_action=(
                        f"Answer at least {min_evidence_questions - answered} more question(s) on "
                        f"{t_name} to gather sufficient evidence."
                    ),
                    related_documents=related_docs,
                )
            )

    demonstrated_topics.sort(key=lambda item: (item.accuracy_percentage, item.topic.lower()))
    insufficient_evidence_topics.sort(
        key=lambda item: (-item.questions_answered, item.topic.lower())
    )
    priority_order = {"high": 0, "moderate": 1, "low": 2}
    recommendations.sort(
        key=lambda r: (priority_order.get(r.priority, 9), r.topic.lower())
    )

    return ReadinessDashboardResponse(
        user_id=user_id,
        unit_id=unit_id,
        min_evidence_questions=min_evidence_questions,
        total_attempts=len(scoped),
        total_questions_answered=total_questions_answered,
        total_correct_answers=total_correct_answers,
        overall_accuracy_percentage=overall_accuracy,
        demonstrated_topics=demonstrated_topics,
        insufficient_evidence_topics=insufficient_evidence_topics,
        recommendations=recommendations,
        recent_attempts=list(reversed(recent_attempts)),
        note=READINESS_NOTE,
    )
