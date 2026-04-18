from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from app.db.session import db_session_dependency
from app.main import app
from app.schemas.overview import (
    EvaluationLeaderboardResponse,
    EvaluationLeaderboardRowResponse,
    EvaluationStatsResponse,
    QuestionStatsResponse,
)


client = TestClient(app)


def test_overview_questions_route_returns_question_stats(monkeypatch) -> None:
    def fake_get_question_stats(session) -> QuestionStatsResponse:
        return QuestionStatsResponse(
            total_questions=136,
            questions_with_content_images=91,
            questions_with_answer_images=12,
            questions_with_analysis_images=8,
        )

    monkeypatch.setattr("app.api.routes.overview.get_question_stats", fake_get_question_stats)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.get("/api/v1/overview/questions")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total_questions"] == 136


def test_overview_evaluations_route_returns_evaluation_stats(monkeypatch) -> None:
    def fake_get_evaluation_stats(session) -> EvaluationStatsResponse:
        return EvaluationStatsResponse(
            total_eval_rows=1088,
            attempt_1_completed=1088,
            attempt_2_completed=124,
            attempt_3_completed=21,
        )

    monkeypatch.setattr("app.api.routes.overview.get_evaluation_stats", fake_get_evaluation_stats)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.get("/api/v1/overview/evaluations")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["attempt_2_completed"] == 124


def test_overview_evaluation_leaderboard_route_returns_model_rows(monkeypatch) -> None:
    def fake_get_evaluation_leaderboard(session) -> EvaluationLeaderboardResponse:
        return EvaluationLeaderboardResponse(
            items=[
                EvaluationLeaderboardRowResponse(
                    model_id=1,
                    model_name="GPT",
                    api_style="chat_completions",
                    api_model="gpt-5.4",
                    release_date=date(2026, 3, 5),
                    is_active=True,
                    sort_order=10,
                    sample_count=136,
                    attempt_1_run_count=136,
                    attempt_1_correct_count=108,
                    attempt_1_error_count=2,
                    attempt_2_run_count=28,
                    attempt_2_incremental_correct_count=6,
                    attempt_2_cumulative_correct_count=114,
                    attempt_3_run_count=9,
                    attempt_3_incremental_correct_count=1,
                    attempt_3_cumulative_correct_count=115,
                    latest_finished_at=datetime(2026, 4, 17, 9, 0, tzinfo=UTC),
                )
            ]
        )

    monkeypatch.setattr(
        "app.api.routes.overview.get_evaluation_leaderboard",
        fake_get_evaluation_leaderboard,
    )
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.get("/api/v1/overview/evaluation-leaderboard")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["items"][0]["model_name"] == "GPT"
    assert body["items"][0]["attempt_3_cumulative_correct_count"] == 115
