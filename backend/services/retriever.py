from __future__ import annotations

import re
from typing import Iterable, List, Optional

from backend.schemas.documents import (
    DocumentCategory,
    DocumentChunkRecord,
    RetrievedChunkResult,
    SourceMetadata,
)


def _tokenize(text: str) -> List[str]:
    return [tok for tok in re.findall(r"[a-z0-9_]+", text.lower()) if len(tok) > 1]


def retrieve_chunks_from_records(
    records: Iterable[DocumentChunkRecord],
    *,
    user_id: str,
    unit_id: str,
    query: str,
    top_k: int = 5,
    category: Optional[DocumentCategory] = None,
) -> List[RetrievedChunkResult]:
    query_tokens = _tokenize(query)
    query_lower = query.lower().strip()

    scoped = [
        rec
        for rec in records
        if rec.user_id == user_id
        and rec.unit_id == unit_id
        and (category is None or rec.category == category)
    ]

    scored: List[tuple[float, DocumentChunkRecord]] = []
    for rec in scoped:
        content_lower = rec.content.lower()
        title_lower = rec.document_title.lower()

        token_hits = sum(content_lower.count(tok) for tok in query_tokens)
        title_hits = sum(2.0 for tok in query_tokens if tok in title_lower)
        phrase_bonus = 3.0 if query_lower and query_lower in content_lower else 0.0
        score = float(token_hits) + title_hits + phrase_bonus

        if score > 0:
            scored.append((score, rec))

    scored.sort(key=lambda pair: (-pair[0], pair[1].document_id, pair[1].chunk_index))

    return [
        RetrievedChunkResult(
            chunk_id=rec.chunk_id,
            content=rec.content,
            score=score,
            source=SourceMetadata(
                document_id=rec.document_id,
                document_title=rec.document_title,
                category=rec.category,
                unit_id=rec.unit_id,
                page_number=rec.page_number,
                chunk_index=rec.chunk_index,
            ),
        )
        for score, rec in scored[:top_k]
    ]
