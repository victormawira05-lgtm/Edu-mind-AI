from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set
from uuid import uuid4

from backend.schemas.documents import DocumentCategory, DocumentChunkRecord
from backend.schemas.past_papers import (
    EvidencePointer,
    ExtractedPastPaperQuestion,
    LectureLink,
    NON_GUARANTEE_DISCLAIMER,
    PastPaperInsightsResponse,
    QuestionType,
    TopicRecurrenceEntry,
)


_QUESTION_SPLIT_RE = re.compile(
    r"(?=(?:\b(?:Question|Q\.?|Part)\s*\d+[a-zA-Z0-9\)\.]*[:\.\)]|\(\s*[a-zA-Z0-9]+\s*\)))",
    re.IGNORECASE,
)

_STOPWORDS: Set[str] = {
    "the", "and", "for", "with", "that", "this", "from", "what", "which",
    "where", "when", "how", "using", "find", "show", "state", "explain",
    "given", "into", "your", "have", "will", "does", "are", "was", "were",
}


def _tokenize_content(text: str) -> List[str]:
    return [
        tok
        for tok in re.findall(r"[a-z0-9]+", text.lower())
        if len(tok) > 2 and tok not in _STOPWORDS
    ]


def _classify_question_type(text: str) -> QuestionType:
    lower = text.lower()
    if any(k in lower for k in ("prove", "show that", "derive", "verify identity")):
        return QuestionType.PROOF_OR_DERIVATION
    if any(
        k in lower
        for k in (
            "calculate", "compute", "evaluate", "differentiate", "integrate",
            "solve for", "derivative", "integral", "limit",
        )
    ):
        return QuestionType.CALCULATION
    if any(k in lower for k in ("define", "what is", "distinguish", "explain why", "describe")):
        return QuestionType.CONCEPTUAL
    return QuestionType.SHORT_ANSWER


def _classify_topic(text: str, lecture_chunks: List[DocumentChunkRecord]) -> str:
    q_tokens = set(_tokenize_content(text))
    best_topic: str | None = None
    best_overlap = 0

    for l_chunk in lecture_chunks:
        l_tokens = set(_tokenize_content(l_chunk.content))
        overlap = len(q_tokens & l_tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best_topic = l_chunk.document_title

    if best_topic and best_overlap >= 2:
        return best_topic

    known_keywords = [
        ("derivative", "Derivatives & Rates of Change"),
        ("differentiate", "Derivatives & Rates of Change"),
        ("chain rule", "Chain Rule & Composite Functions"),
        ("integral", "Integrals & Antiderivatives"),
        ("integrate", "Integrals & Antiderivatives"),
        ("limit", "Limits & Continuity"),
        ("matrix", "Matrices & Linear Systems"),
        ("probability", "Probability & Distributions"),
    ]
    lower = text.lower()
    for needle, label in known_keywords:
        if needle in lower:
            return label

    tokens = _tokenize_content(text)
    if tokens:
        return f"Topic: {tokens[0].capitalize()}"
    return "General Unit Topic"


def _find_lecture_links(
    question_text: str,
    lecture_chunks: List[DocumentChunkRecord],
    max_links: int = 2,
) -> List[LectureLink]:
    q_tokens = set(_tokenize_content(question_text))
    if not q_tokens:
        return []

    scored: List[tuple[float, DocumentChunkRecord]] = []
    for l_chunk in lecture_chunks:
        l_tokens = set(_tokenize_content(l_chunk.content))
        overlap = len(q_tokens & l_tokens)
        if overlap > 0:
            score = round(overlap / max(1, len(q_tokens)), 3)
            scored.append((score, l_chunk))

    scored.sort(key=lambda pair: (-pair[0], pair[1].document_id, pair[1].chunk_index))

    links: List[LectureLink] = []
    for score, chunk in scored[:max_links]:
        links.append(
            LectureLink(
                lecture_document_id=chunk.document_id,
                lecture_document_title=chunk.document_title,
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                relevance_score=score,
                excerpt=chunk.content[:220],
            )
        )
    return links


def analyze_unit_past_papers(
    chunks: Iterable[DocumentChunkRecord],
    *,
    user_id: str,
    unit_id: str,
) -> PastPaperInsightsResponse:
    scoped_chunks = [c for c in chunks if c.user_id == user_id and c.unit_id == unit_id]
    past_paper_chunks = [c for c in scoped_chunks if c.category == DocumentCategory.PAST_PAPER]
    lecture_chunks = [c for c in scoped_chunks if c.category == DocumentCategory.LECTURE_NOTES]

    paper_ids: Set[str] = {c.document_id for c in past_paper_chunks}
    extracted: List[ExtractedPastPaperQuestion] = []

    q_counter = 0
    for chunk in past_paper_chunks:
        raw_parts = [p.strip() for p in _QUESTION_SPLIT_RE.split(chunk.content) if p.strip()]
        candidates = raw_parts if raw_parts else [chunk.content.strip()]

        for part in candidates:
            if len(part) < 12:
                continue
            q_counter += 1
            label_match = re.match(
                r"^((?:Question|Q\.?|Part)\s*\d+[a-zA-Z0-9\)\.]*|\(\s*[a-zA-Z0-9]+\s*\))",
                part,
                re.IGNORECASE,
            )
            q_label = label_match.group(1).strip() if label_match else f"Q{q_counter}"
            q_type = _classify_question_type(part)
            topic = _classify_topic(part, lecture_chunks)
            links = _find_lecture_links(part, lecture_chunks)

            evidence = EvidencePointer(
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                excerpt=part[:240],
            )

            extracted.append(
                ExtractedPastPaperQuestion(
                    question_id=f"ppq-{uuid4().hex[:8]}-{q_counter}",
                    unit_id=unit_id,
                    question_label=q_label,
                    question_text=part,
                    topic=topic,
                    question_type=q_type,
                    source_evidence=evidence,
                    lecture_links=links,
                )
            )

    grouped: Dict[str, List[ExtractedPastPaperQuestion]] = {}
    for q in extracted:
        grouped.setdefault(q.topic, []).append(q)

    recurrence: List[TopicRecurrenceEntry] = []
    for topic_name, items in grouped.items():
        distinct_papers = {item.source_evidence.document_id for item in items}
        distinct_types: List[QuestionType] = []
        for item in items:
            if item.question_type not in distinct_types:
                distinct_types.append(item.question_type)

        ev_list = [item.source_evidence for item in items]

        seen_link_keys: Set[tuple[str, str]] = set()
        merged_links: List[LectureLink] = []
        for item in items:
            for link in item.lecture_links:
                key = (link.lecture_document_id, link.chunk_id)
                if key not in seen_link_keys:
                    seen_link_keys.add(key)
                    merged_links.append(link)

        recurrence.append(
            TopicRecurrenceEntry(
                topic=topic_name,
                occurrence_count=len(items),
                paper_count=len(distinct_papers),
                question_types=distinct_types,
                evidence=ev_list,
                linked_lectures=merged_links,
            )
        )

    recurrence.sort(key=lambda r: (-r.occurrence_count, r.topic))

    return PastPaperInsightsResponse(
        unit_id=unit_id,
        analyzed_paper_count=len(paper_ids),
        extracted_questions=extracted,
        recurrence=recurrence,
        disclaimer=NON_GUARANTEE_DISCLAIMER,
    )
