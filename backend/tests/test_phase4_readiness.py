from fastapi.testclient import TestClient

from backend import main as backend_main
from backend.providers.base import AIProvider
from backend.schemas.quiz import GeneratedQuizItem, GeneratedQuizPayload


class MultiTopicQuizProvider(AIProvider):
    def generate_quiz(
        self,
        *,
        topic: str,
        num_questions: int,
        context_excerpt=None,
        lecture_title=None,
    ) -> GeneratedQuizPayload:
        return GeneratedQuizPayload(
            title=f"{topic} Quiz",
            questions=[
                GeneratedQuizItem(
                    id="q-1",
                    prompt="Question 1 on Derivatives",
                    options=["A", "B", "C"],
                    correct_option_index=0,
                    explanation="Option A is correct.",
                    topic="Derivatives",
                ),
                GeneratedQuizItem(
                    id="q-2",
                    prompt="Question 2 on Derivatives",
                    options=["A", "B", "C"],
                    correct_option_index=1,
                    explanation="Option B is correct.",
                    topic="Derivatives",
                ),
                GeneratedQuizItem(
                    id="q-3",
                    prompt="Question 3 on Derivatives",
                    options=["A", "B", "C"],
                    correct_option_index=2,
                    explanation="Option C is correct.",
                    topic="Derivatives",
                ),
                GeneratedQuizItem(
                    id="q-4",
                    prompt="Question 4 on Integrals (single sample)",
                    options=["A", "B", "C"],
                    correct_option_index=0,
                    explanation="Option A is correct.",
                    topic="Integrals",
                ),
            ][:num_questions],
        )

    def generate_answer(self, *, prompt: str, context: str) -> str:
        return "Stub answer."


def setup_function():
    backend_main.STORE.workspaces.clear()
    backend_main.STORE.quizzes.clear()
    backend_main.STORE.attempts.clear()
    backend_main.STORE.attempt_entries.clear()
    backend_main.STORE.documents.clear()
    backend_main.STORE.chunks.clear()
    backend_main.AI_PROVIDER = MultiTopicQuizProvider()


def test_readiness_separates_demonstrated_vs_insufficient_evidence_and_history(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH_BYPASS", "true")
    client = TestClient(backend_main.app)
    headers = {"X-Dev-User-Id": "student-alice"}

    gen_res = client.post(
        "/api/quizzes/generate",
        headers=headers,
        json={"topic": "Calculus", "num_questions": 4, "unit_id": "MAT120"},
    )
    assert gen_res.status_code == 201
    quiz_id = gen_res.json()["quiz_id"]

    sub_res = client.post(
        f"/api/quizzes/{quiz_id}/submit",
        headers=headers,
        json={
            "answers": [
                {"question_id": "q-1", "selected_option_index": 0},
                {"question_id": "q-2", "selected_option_index": 0},
                {"question_id": "q-3", "selected_option_index": 0},
                {"question_id": "q-4", "selected_option_index": 0},
            ]
        },
    )
    assert sub_res.status_code == 200

    dash_res = client.get("/api/readiness", headers=headers, params={"unit_id": "MAT120"})
    assert dash_res.status_code == 200
    dash = dash_res.json()

    assert dash["total_attempts"] == 1
    assert dash["total_questions_answered"] == 4
    assert dash["total_correct_answers"] == 2
    assert dash["overall_accuracy_percentage"] == 50.0

    demo_names = [t["topic"] for t in dash["demonstrated_topics"]]
    insuff_names = [t["topic"] for t in dash["insufficient_evidence_topics"]]
    assert demo_names == ["Derivatives"]
    assert insuff_names == ["Integrals"]
    assert dash["insufficient_evidence_topics"][0]["evidence_status"] == "insufficient_evidence"

    assert len(dash["recommendations"]) == 2
    assert dash["recommendations"][0]["topic"] == "Derivatives"
    assert dash["recommendations"][0]["priority"] == "high"

    hist_res = client.get("/api/quizzes/history", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 1

    other_hist = client.get(
        "/api/quizzes/history", headers={"X-Dev-User-Id": "student-bob"}
    )
    assert other_hist.status_code == 200
    assert other_hist.json() == []
