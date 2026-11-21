from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from backend.repositories.base import StoredQuizRecord, StudyRepository
from backend.schemas.documents import (
    DocumentCategory,
    DocumentChunkRecord,
    UploadedDocumentSummary,
)
from backend.schemas.past_papers import (
    EvidencePointer,
    ExtractedPastPaperQuestion,
    LectureLink,
    NON_GUARANTEE_DISCLAIMER,
    PastPaperInsightsResponse,
    QuestionType,
    TopicRecurrenceEntry,
)
from backend.schemas.quiz import (
    GeneratedQuizPayload,
    QuizAttemptResult,
    QuestionGradeResult,
    WorkspaceProfilePayload,
)
from backend.services.readiness_analyzer import AttemptRecordEntry


class PostgresRepository(StudyRepository):
    """
    PostgreSQL / Supabase repository scoped by user_id and unit_id.
    Expects migrations 002, 003, and 004 to be applied.
    """

    def __init__(self, database_url: str) -> None:
        if not database_url or not database_url.strip():
            raise ValueError("DATABASE_URL must be configured for PostgresRepository.")
        self._database_url = database_url.strip()

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._database_url, row_factory=dict_row)

    @staticmethod
    def _normalize_unit(unit_id: Optional[str]) -> Optional[str]:
        if unit_id is None:
            return None
        cleaned = unit_id.strip()
        return cleaned or None

    # --- Workspace (P1) ---
    # Note: Ensure a workspace_profiles table exists if persisting workspaces in Postgres.
    def get_workspace(self, user_id: str) -> WorkspaceProfilePayload:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select payload_json
                from public.workspace_profiles
                where user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return WorkspaceProfilePayload()
            raw = row["payload_json"]
            data = json.loads(raw) if isinstance(raw, str) else raw
            return WorkspaceProfilePayload.model_validate(data)

    def upsert_workspace(
        self, user_id: str, profile: WorkspaceProfilePayload
    ) -> WorkspaceProfilePayload:
        serialized = profile.model_dump_json()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.workspace_profiles (user_id, payload_json, updated_at)
                values (%s, %s::jsonb, now())
                on conflict (user_id)
                do update set payload_json = excluded.payload_json, updated_at = now()
                """,
                (user_id, serialized),
            )
            conn.commit()
        return profile

    # --- Documents & Chunks (Migration 002) ---
    def save_document_with_chunks(
        self,
        user_id: str,
        summary: UploadedDocumentSummary,
        chunks: List[DocumentChunkRecord],
    ) -> UploadedDocumentSummary:
        norm_unit = self._normalize_unit(summary.unit_id) or "general"
        doc_uuid = str(UUID(summary.document_id))

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.unit_documents (
                    id, user_id, unit_id, title, filename, category,
                    page_count, extracted_chars, chunk_count
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_uuid,
                    user_id,
                    norm_unit,
                    summary.title,
                    summary.filename,
                    summary.category.value,
                    summary.page_count,
                    summary.extracted_chars,
                    len(chunks),
                ),
            )
            for ch in chunks:
                cur.execute(
                    """
                    insert into public.document_chunks (
                        chunk_id, user_id, unit_id, document_id, document_title,
                        category, page_number, chunk_index, content
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        ch.chunk_id,
                        user_id,
                        norm_unit,
                        doc_uuid,
                        ch.document_title,
                        ch.category.value,
                        ch.page_number,
                        ch.chunk_index,
                        ch.content,
                    ),
                )
            conn.commit()

        return summary.model_copy(
            update={"user_id": user_id, "unit_id": norm_unit, "chunk_count": len(chunks)}
        )

    def list_documents(
        self, user_id: str, unit_id: str
    ) -> List[UploadedDocumentSummary]:
        norm_unit = self._normalize_unit(unit_id) or "general"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select id, user_id, unit_id, title, filename, category,
                       page_count, extracted_chars, chunk_count
                from public.unit_documents
                where user_id = %s and unit_id = %s
                order by uploaded_at desc
                """,
                (user_id, norm_unit),
            )
            rows = cur.fetchall()

        return [
            UploadedDocumentSummary(
                document_id=str(r["id"]),
                user_id=str(r["user_id"]),
                unit_id=r["unit_id"],
                title=r["title"],
                filename=r["filename"],
                category=DocumentCategory(r["category"]),
                page_count=r["page_count"],
                extracted_chars=r["extracted_chars"],
                chunk_count=r["chunk_count"],
            )
            for r in rows
        ]

    def list_chunks(
        self,
        user_id: str,
        unit_id: str,
        category: Optional[DocumentCategory] = None,
    ) -> List[DocumentChunkRecord]:
        norm_unit = self._normalize_unit(unit_id) or "general"
        query = """
            select chunk_id, user_id, unit_id, document_id, document_title,
                   category, page_number, chunk_index, content
            from public.document_chunks
            where user_id = %s and unit_id = %s
        """
        params: List[Any] = [user_id, norm_unit]
        if category is not None:
            query += " and category = %s"
            params.append(category.value)
        query += " order by document_id, page_number, chunk_index"

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        return [
            DocumentChunkRecord(
                chunk_id=r["chunk_id"],
                user_id=str(r["user_id"]),
                unit_id=r["unit_id"],
                document_id=str(r["document_id"]),
                document_title=r["document_title"],
                category=DocumentCategory(r["category"]),
                page_number=r["page_number"],
                chunk_index=r["chunk_index"],
                content=r["content"],
            )
            for r in rows
        ]

    # --- Quizzes & Attempts (Migration 004) ---
    def save_quiz(
        self,
        user_id: str,
        quiz_id: str,
        unit_id: Optional[str],
        payload: GeneratedQuizPayload,
    ) -> StoredQuizRecord:
        norm_unit = self._normalize_unit(unit_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.quiz_definitions (quiz_id, owner_user_id, unit_id, payload_json)
                values (%s, %s, %s, %s::jsonb)
                on conflict (quiz_id)
                do update set unit_id = excluded.unit_id, payload_json = excluded.payload_json
                """,
                (quiz_id, user_id, norm_unit, payload.model_dump_json()),
            )
            conn.commit()
        return StoredQuizRecord(
            quiz_id=quiz_id,
            owner_user_id=user_id,
            unit_id=norm_unit,
            payload=payload,
        )

    def get_quiz(self, quiz_id: str) -> Optional[StoredQuizRecord]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select quiz_id, owner_user_id, unit_id, payload_json
                from public.quiz_definitions
                where quiz_id = %s
                """,
                (quiz_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        raw = row["payload_json"]
        data = json.loads(raw) if isinstance(raw, str) else raw
        return StoredQuizRecord(
            quiz_id=row["quiz_id"],
            owner_user_id=str(row["owner_user_id"]),
            unit_id=row["unit_id"],
            payload=GeneratedQuizPayload.model_validate(data),
        )

    def record_attempt(
        self,
        user_id: str,
        unit_id: Optional[str],
        result: QuizAttemptResult,
    ) -> None:
        norm_unit = self._normalize_unit(unit_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.quiz_attempts (
                    attempt_id, quiz_id, user_id, unit_id, title,
                    score, total_questions, percentage
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    result.attempt_id,
                    result.quiz_id,
                    user_id,
                    norm_unit,
                    result.title,
                    result.score,
                    result.total_questions,
                    result.percentage,
                ),
            )
            for q in result.results:
                cur.execute(
                    """
                    insert into public.topic_attempt_answers (
                        attempt_id, user_id, unit_id, topic, question_id, is_correct
                    )
                    values (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        result.attempt_id,
                        user_id,
                        norm_unit,
                        q.topic.strip() or "General",
                        q.question_id,
                        q.is_correct,
                    ),
                )
            conn.commit()

    def list_attempt_entries(
        self, user_id: str, unit_id: Optional[str] = None
    ) -> List[AttemptRecordEntry]:
        norm_unit = self._normalize_unit(unit_id)
        attempt_sql = """
            select attempt_id, quiz_id, unit_id, title, score, total_questions, percentage
            from public.quiz_attempts
            where user_id = %s
        """
        attempt_params: List[Any] = [user_id]
        if norm_unit is not None:
            attempt_sql += " and unit_id = %s"
            attempt_params.append(norm_unit)
        attempt_sql += " order by created_at asc"

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(attempt_sql, attempt_params)
            attempt_rows = cur.fetchall()
            if not attempt_rows:
                return []

            attempt_ids = [r["attempt_id"] for r in attempt_rows]
            cur.execute(
                """
                select attempt_id, question_id, topic, is_correct
                from public.topic_attempt_answers
                where user_id = %s and attempt_id = any(%s)
                """,
                (user_id, attempt_ids),
            )
            answer_rows = cur.fetchall()

        answers_by_attempt: Dict[str, List[QuestionGradeResult]] = {}
        for a in answer_rows:
            answers_by_attempt.setdefault(a["attempt_id"], []).append(
                QuestionGradeResult(
                    question_id=a["question_id"],
                    is_correct=bool(a["is_correct"]),
                    selected_option_index=0,
                    correct_option_index=0,
                    explanation="",
                    topic=a["topic"],
                )
            )

        entries: List[AttemptRecordEntry] = []
        for r in attempt_rows:
            aid = r["attempt_id"]
            res = QuizAttemptResult(
                attempt_id=aid,
                quiz_id=r["quiz_id"],
                title=r["title"],
                score=r["score"],
                total_questions=r["total_questions"],
                percentage=float(r["percentage"]),
                results=answers_by_attempt.get(aid, []),
            )
            entries.append(
                AttemptRecordEntry(
                    user_id=user_id,
                    unit_id=r["unit_id"],
                    result=res,
                )
            )
        return entries

    # --- Past-Paper Insights (Migration 003) ---
    def save_past_paper_insights(
        self, user_id: str, unit_id: str, insights: PastPaperInsightsResponse
    ) -> None:
        norm_unit = self._normalize_unit(unit_id) or "general"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                delete from public.question_lecture_links
                where user_id = %s and question_id in (
                    select question_id from public.past_paper_questions
                    where user_id = %s and unit_id = %s
                )
                """,
                (user_id, user_id, norm_unit),
            )
            cur.execute(
                """
                delete from public.past_paper_questions
                where user_id = %s and unit_id = %s
                """,
                (user_id, norm_unit),
            )
            for q in insights.extracted_questions:
                ev = q.source_evidence
                cur.execute(
                    """
                    insert into public.past_paper_questions (
                        question_id, user_id, unit_id, document_id, document_title,
                        page_number, chunk_id, question_label, question_text,
                        topic, question_type, excerpt
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        q.question_id,
                        user_id,
                        norm_unit,
                        ev.document_id,
                        ev.document_title,
                        ev.page_number,
                        ev.chunk_id,
                        q.question_label,
                        q.question_text,
                        q.topic,
                        q.question_type.value,
                        ev.excerpt,
                    ),
                )
                for link in q.lecture_links:
                    cur.execute(
                        """
                        insert into public.question_lecture_links (
                            question_id, user_id, lecture_document_id,
                            lecture_document_title, page_number, chunk_id,
                            relevance_score, excerpt
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (question_id, chunk_id) do nothing
                        """,
                        (
                            q.question_id,
                            user_id,
                            link.lecture_document_id,
                            link.lecture_document_title,
                            link.page_number,
                            link.chunk_id,
                            link.relevance_score,
                            link.excerpt,
                        ),
                    )
            conn.commit()

    def get_saved_past_paper_insights(
        self, user_id: str, unit_id: str
    ) -> Optional[PastPaperInsightsResponse]:
        norm_unit = self._normalize_unit(unit_id) or "general"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select question_id, unit_id, document_id, document_title,
                       page_number, chunk_id, question_label, question_text,
                       topic, question_type, excerpt
                from public.past_paper_questions
                where user_id = %s and unit_id = %s
                order by created_at asc, question_id asc
                """,
                (user_id, norm_unit),
            )
            q_rows = cur.fetchall()
            if not q_rows:
                return None

            q_ids = [r["question_id"] for r in q_rows]
            cur.execute(
                """
                select question_id, lecture_document_id, lecture_document_title,
                       page_number, chunk_id, relevance_score, excerpt
                from public.question_lecture_links
                where user_id = %s and question_id = any(%s)
                order by relevance_score desc, chunk_id asc
                """,
                (user_id, q_ids),
            )
            link_rows = cur.fetchall()

        links_by_q: Dict[str, List[LectureLink]] = {}
        for lr in link_rows:
            links_by_q.setdefault(lr["question_id"], []).append(
                LectureLink(
                    lecture_document_id=str(lr["lecture_document_id"]),
                    lecture_document_title=lr["lecture_document_title"],
                    page_number=lr["page_number"],
                    chunk_id=lr["chunk_id"],
                    relevance_score=float(lr["relevance_score"]),
                    excerpt=lr["excerpt"],
                )
            )

        extracted: List[ExtractedPastPaperQuestion] = []
        paper_ids: Set[str] = set()
        for qr in q_rows:
            doc_id_str = str(qr["document_id"])
            paper_ids.add(doc_id_str)
            ev = EvidencePointer(
                document_id=doc_id_str,
                document_title=qr["document_title"],
                page_number=qr["page_number"],
                chunk_id=qr["chunk_id"],
                excerpt=qr["excerpt"],
            )
            extracted.append(
                ExtractedPastPaperQuestion(
                    question_id=qr["question_id"],
                    unit_id=qr["unit_id"],
                    question_label=qr["question_label"],
                    question_text=qr["question_text"],
                    topic=qr["topic"],
                    question_type=QuestionType(qr["question_type"]),
                    source_evidence=ev,
                    lecture_links=links_by_q.get(qr["question_id"], []),
                )
            )

        grouped: Dict[str, List[ExtractedPastPaperQuestion]] = {}
        for q in extracted:
            grouped.setdefault(q.topic, []).append(q)

        recurrence: List[TopicRecurrenceEntry] = []
        for topic_name, items in grouped.items():
            distinct_papers = {it.source_evidence.document_id for it in items}
            distinct_types: List[QuestionType] = []
            for it in items:
                if it.question_type not in distinct_types:
                    distinct_types.append(it.question_type)
            ev_list = [it.source_evidence for it in items]

            seen_keys: Set[Tuple[str, str]] = set()
            merged_links: List[LectureLink] = []
            for it in items:
                for lk in it.lecture_links:
                    key = (lk.lecture_document_id, lk.chunk_id)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        merged_links.append(lk)

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
            unit_id=norm_unit,
            analyzed_paper_count=len(paper_ids),
            extracted_questions=extracted,
            recurrence=recurrence,
            disclaimer=NON_GUARANTEE_DISCLAIMER,
        )
