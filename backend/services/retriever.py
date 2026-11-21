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
    """
    PostgreSQL-style / unit-scoped keyword + metadata retrieval.
    Strictly filters by authenticated user_id and unit_id before scoring.
    Semantic vector search (pgvector) is intentionally deferred until required.
    """
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

    results: List[RetrievedChunkResult] = []
    for score, rec in scored[:top_k]:
        results.append(
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
        )
    return results


class PostgresChunkRetriever:
    """
    Optional live PostgreSQL / Supabase Postgres full-text retriever using psycopg
    when DATABASE_URL is configured; no microservices introduced.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def search(
        self,
        *,
        user_id: str,
        unit_id: str,
        query: str,
        top_k: int = 5,
        category: Optional[DocumentCategory] = None,
    ) -> List[RetrievedChunkResult]:
        import psycopg  # imported only when live Postgres retrieval is invoked

        sql = """
            SELECT
                chunk_id,
                document_id,
                document_title,
                category,
                unit_id,
                page_number,
                chunk_index,
                content,
                ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', %s)) AS rank
            FROM public.document_chunks
            WHERE user_id = %s
              AND unit_id = %s
              AND (%s::text IS NULL OR category = %s::text)
              AND to_tsvector('english', content) @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC, chunk_index ASC
            LIMIT %s
        """
        cat_val = category.value if category else None
        params = (query, user_id, unit_id, cat_val, cat_val, query, top_k)

        rows = []
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        return [
            RetrievedChunkResult(
                chunk_id=r[0],
                content=r[7],
                score=float(r[8] or 0.0),
                source=SourceMetadata(
                    document_id=r[1],
                    document_title=r[2],
                    category=DocumentCategory(r[3]),
                    unit_id=r[4],
                    page_number=int(r[5]),
                    chunk_index=int(r[6]),
                ),
            )
            for r in rows
        ]
