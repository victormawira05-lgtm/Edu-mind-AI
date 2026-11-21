from __future__ import annotations

import json
import os
import re
from typing import List, Optional

from backend.providers.base import AIProvider
from backend.schemas.quiz import GeneratedQuizItem, GeneratedQuizPayload, LectureReference

DEFAULT_GEMINI_MODELS: List[str] = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]


def _extract_json_object(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    return json.loads(cleaned)


def _is_retryable_model_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in ("404", "not found", "503", "unavailable", "high demand", "429", "resource_exhausted")
    )


class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, models: Optional[List[str]] = None) -> None:
        self.api_key = (
            api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        ).strip()
        env_models = [m.strip() for m in os.getenv("GEMINI_MODELS", "").split(",") if m.strip()]
        self.models = models or env_models or list(DEFAULT_GEMINI_MODELS)

    def _build_client(self):
        from google import genai
        return genai.Client(api_key=self.api_key)

    def _call_models(self, prompt: str, json_mode: bool = False) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        client = self._build_client()
        last_err: Optional[Exception] = None
        for model_name in self.models:
            try:
                if json_mode:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"response_mime_type": "application/json"},
                    )
                else:
                    response = client.models.generate_content(model=model_name, contents=prompt)
                text = getattr(response, "text", None) or ""
                if not text.strip():
                    raise ValueError("Empty response returned from Gemini.")
                return text
            except Exception as exc:
                last_err = exc
                if _is_retryable_model_error(exc):
                    continue
                raise
        raise RuntimeError(f"All configured Gemini models failed. Last error: {last_err}")

    def _local_structured_quiz_fallback(
        self,
        *,
        topic: str,
        num_questions: int,
        context_excerpt: Optional[str],
        lecture_title: Optional[str],
    ) -> GeneratedQuizPayload:
        ref = (
            LectureReference(
                document_title=lecture_title,
                section_or_page="Study Notes",
                excerpt=(context_excerpt[:180] if context_excerpt else None),
            )
            if (lecture_title or context_excerpt)
            else None
        )
        items: List[GeneratedQuizItem] = []
        for idx in range(num_questions):
            q_num = idx + 1
            items.append(
                GeneratedQuizItem(
                    id=f"q-{q_num}",
                    prompt=f"[{topic}] Concept check #{q_num}: Which approach best supports learning {topic}?",
                    options=[
                        f"Review core definitions, worked examples, and key assumptions for {topic}",
                        "Memorize isolated formulas without checking conditions or context",
                        "Ignore worked examples and edge cases",
                        "Skip checking intermediate reasoning steps",
                    ],
                    correct_option_index=0,
                    explanation=(
                        f"Mastering {topic} relies on connecting definitions with worked examples "
                        f"and checking assumptions step by step."
                    ),
                    topic=topic,
                    lecture_reference=ref,
                )
            )
        return GeneratedQuizPayload(title=f"{topic} Practice Quiz", questions=items)

    def generate_quiz(
        self,
        *,
        topic: str,
        num_questions: int,
        context_excerpt: Optional[str] = None,
        lecture_title: Optional[str] = None,
    ) -> GeneratedQuizPayload:
        if not self.api_key:
            return self._local_structured_quiz_fallback(
                topic=topic,
                num_questions=num_questions,
                context_excerpt=context_excerpt,
                lecture_title=lecture_title,
            )
        ref_hint = f"Lecture/Document title: {lecture_title}\n" if lecture_title else ""
        ctx_hint = f"Study excerpt:\n{context_excerpt[:3500]}\n" if context_excerpt else ""
        prompt = (
            "You are EduMind AI. Create a multiple-choice quiz as strict JSON only.\n"
            f"Topic: {topic}\nNumber of questions: {num_questions}\n{ref_hint}{ctx_hint}\n"
            'Return JSON: {"title": "string", "questions": [{"id": "q-1", "prompt": "string", '
            '"options": ["A", "B", "C", "D"], "correct_option_index": 0, "explanation": "string", '
            '"topic": "string", "lecture_reference": null}]}'
        )
        raw = self._call_models(prompt, json_mode=True)
        return GeneratedQuizPayload.model_validate(_extract_json_object(raw))

    def generate_answer(self, *, prompt: str, context: str) -> str:
        if not self.api_key:
            return f"Study guide for '{prompt}': Focus on core definitions, worked examples, and step-by-step checks."
        full_prompt = (
            "You are EduMind AI, a supportive study tutor. Answer clearly using bullet points "
            f"and step-by-step reasoning.\nContext:\n{context[:3500]}\n\nQuestion: {prompt}"
        )
        return self._call_models(full_prompt, json_mode=False)
