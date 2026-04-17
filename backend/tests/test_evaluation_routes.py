from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.session import db_session_dependency
from app.main import app
from app.schemas.evaluation import (
    EvaluationPayloadPreviewResponse,
    EvaluationPreviewResponse,
    EvaluationRunResponse,
)


client = TestClient(app)


def test_preview_route_returns_only_content_images(monkeypatch) -> None:
    def fake_preview(session, payload) -> EvaluationPreviewResponse:
        assert payload.question_id == 9
        assert payload.model_id == 1
        return EvaluationPreviewResponse(
            question_id=9,
            model_id=1,
            model_name="GPT",
            model_is_active=True,
            model_is_configured=True,
            prompt_text="题目文本",
            content_image_paths=["images/0009_content_1.png"],
        )

    monkeypatch.setattr("app.api.routes.evaluations.preview_evaluation", fake_preview)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.post("/api/v1/evaluations/preview", json={"question_id": 9, "model_id": 1})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["content_image_paths"] == ["images/0009_content_1.png"]


def test_run_route_returns_attempt_result(monkeypatch) -> None:
    def fake_run(session, payload) -> EvaluationRunResponse:
        assert payload.attempt == 1
        return EvaluationRunResponse(
            eval_result_id=99,
            question_id=9,
            model_id=1,
            model_name="GPT",
            attempt=1,
            attempt_result=1,
            response_text="62平方厘米",
            judge_feedback="模型回复与标准答案一致。",
            error=None,
            finished_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
        )

    monkeypatch.setattr("app.api.routes.evaluations.run_evaluation", fake_run)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.post(
            "/api/v1/evaluations/run",
            json={"question_id": 9, "model_id": 1, "attempt": 1, "persist_result": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "correct"
    assert "judge_feedback" not in response.json()
    assert "response_text" not in response.json()


def test_generate_route_returns_generation_status(monkeypatch) -> None:
    def fake_generate(session, payload) -> EvaluationRunResponse:
        return EvaluationRunResponse(
            eval_result_id=99,
            question_id=9,
            model_id=1,
            model_name="GPT",
            attempt=1,
            attempt_result=None,
            response_text="62平方厘米",
            judge_feedback=None,
            error=None,
            finished_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
        )

    monkeypatch.setattr("app.api.routes.evaluations.generate_evaluation", fake_generate)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.post(
            "/api/v1/evaluations/generate",
            json={"question_id": 9, "model_id": 1, "attempt": 1, "persist_result": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "generated"
    assert "response_text" not in response.json()


def test_judge_route_returns_judge_status(monkeypatch) -> None:
    def fake_judge(session, payload) -> EvaluationRunResponse:
        return EvaluationRunResponse(
            eval_result_id=99,
            question_id=9,
            model_id=1,
            model_name="GPT",
            attempt=1,
            attempt_result=0,
            response_text="62平方厘米",
            judge_feedback="答案不一致",
            error=None,
            finished_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
        )

    monkeypatch.setattr("app.api.routes.evaluations.judge_evaluation", fake_judge)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.post(
            "/api/v1/evaluations/judge",
            json={"question_id": 9, "model_id": 1, "attempt": 1, "persist_result": True},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "incorrect"


def test_payload_preview_route_returns_message_structure(monkeypatch) -> None:
    def fake_payload_preview(session, payload) -> EvaluationPayloadPreviewResponse:
        return EvaluationPayloadPreviewResponse(
            question_id=9,
            model_id=7,
            model_name="Hunyuan",
            api_style="responses",
            api_model="hunyuan-vision-1.5-instruct",
            request_url="https://example.test/v1/responses",
            payload={
                "model": "hunyuan-vision-1.5-instruct",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "如图，求面积。"},
                            {
                                "type": "input_image",
                                "image_url": "data:image/png;base64,abcd...",
                            },
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr(
        "app.api.routes.evaluations.preview_evaluation_payload",
        fake_payload_preview,
    )
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.post(
            "/api/v1/evaluations/payload-preview",
            json={"question_id": 9, "model_id": 7},
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["api_style"] == "responses"
    assert body["request_url"].endswith("/responses")
    assert body["payload"]["input"][0]["content"][0]["type"] == "input_text"
