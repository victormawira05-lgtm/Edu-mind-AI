from fastapi.testclient import TestClient

from backend import main as backend_main
from backend.providers.base import AIProvider
from backend.schemas.quiz import GeneratedQuizItem, GeneratedQuizPayload, LectureReference


class StubAIProvider(AIProvider):
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
                    prompt="What is the derivative of x^2?",
                    options=["2x", "x", "2", "x^2"],
                    correct_option_index=0,
                    explanation="By the power rule, d/dx(x^2) = 2x.",
                    topic="Derivatives",
                    lecture_reference=LectureReference(
                        document_title="Calculus 1 notes",
                        section_or_page="Page 14",
                    ),
                ),
                GeneratedQuizItem(
                    id="q-2",
                    prompt="Which limit equals 1 as x -> 0?",
                    options=["sin(x)/x", "x^2", "1/x", "cos(x) - 1"],
                    correct_option_index=0,
                    explanation="Standard trigonometric limit: lim_{x->0} sin(x)/x = 1.",
                    topic="Limits",
                    lecture_reference=None,
                ),
            ][:num_questions],
        )

    def generate_answer(self, *, prompt: str, context: str) -> str:
        return "Stub tutor answer."


def setup_function():
    backend_main.STORE.workspaces.clear()
    backend_main.STORE.quizzes.clear()
    backend_main.STORE.attempts.clear()
    backend_main.AI_PROVIDER = StubAIProvider()


def test_unauthenticated_requests_rejected(monkeypatch):
    monkeypatch.delenv("ALLOW_DEV_AUTH_BYPASS", raising=False)
    client = TestClient(backend_main.app)

    assert client.get("/api/workspace").status_code == 401
    assert (
        client.post(
            "/api/quizzes/generate",
            json={"topic": "Calculus", "num_questions": 2},
        ).status_code
        == 401
    )


def test_quiz_generated_without_institution_and_graded_deterministically(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH_BYPASS", "true")
    client = TestClient(backend_main.app)
    headers = {"X-Dev-User-Id": "student-alice"}

    gen_res = client.post(
        "/api/quizzes/generate",
        headers=headers,
        json={"topic": "Calculus", "num_questions": 2},
    )
    assert gen_res.status_code == 201
    quiz_data = gen_res.json()
    assert quiz_data["unit_id"] is None
    assert len(quiz_data["questions"]) == 2

    # Ensure answer key is never exposed before submission
    for q in quiz_data["questions"]:
        assert "correct_option_index" not in q

    quiz_id = quiz_data["quiz_id"]
    submit_res = client.post(
        f"/api/quizzes/{quiz_id}/submit",
        headers=headers,
        json={
            "answers": [
                {"question_id": "q-1", "selected_option_index": 0},
                {"question_id": "q-2", "selected_option_index": 2},
            ]
        },
    )
    assert submit_res.status_code == 200
    graded = submit_res.json()
    assert graded["score"] == 1
    assert graded["total_questions"] == 2
    assert graded["percentage"] == 50.0
    assert graded["results"][0]["is_correct"] is True
    assert graded["results"][0]["lecture_reference"]["document_title"] == "Calculus 1 notes"
    assert graded["results"][1]["is_correct"] is False
    assert "sin(x)/x" in graded["results"][1]["explanation"]


def test_cross_user_quiz_submission_forbidden(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH_BYPASS", "true")
    client = TestClient(backend_main.app)

    create_res = client.post(
        "/api/quizzes/generate",
        headers={"X-Dev-User-Id": "student-alice"},
        json={"topic": "Calculus", "num_questions": 1},
    )
    quiz_id = create_res.json()["quiz_id"]

    other_res = client.post(
        f"/api/quizzes/{quiz_id}/submit",
        headers={"X-Dev-User-Id": "student-bob"},
        json={"answers": [{"question_id": "q-1", "selected_option_index": 0}]},
    )
    assert other_res.status_code == 403
