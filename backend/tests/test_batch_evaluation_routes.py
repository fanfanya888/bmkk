from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.db.session import db_session_dependency
from app.main import app
from app.schemas.evaluation import (
    EvaluationBatchJobItemResponse,
    EvaluationBatchJobResponse,
    EvaluationBatchJobSummaryResponse,
)


client = TestClient(app)


def build_batch_job_response() -> EvaluationBatchJobResponse:
    return EvaluationBatchJobResponse(
        job_id="job-1",
        model_id=7,
        model_name="Hunyuan",
        attempt=1,
        execution_mode="generate_and_judge",
        selection_mode="pending_limit",
        persist_result=True,
        request_timeout_seconds=120.0,
        force=False,
        status="running",
        total_questions=3,
        completed_questions=1,
        current_question_id=10,
        generated_count=0,
        correct_count=1,
        incorrect_count=0,
        error_count=0,
        unknown_count=0,
        cancelled_count=0,
        created_at=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
        started_at=datetime(2026, 4, 15, 10, 1, tzinfo=UTC),
        finished_at=None,
        job_error=None,
        items=[
            EvaluationBatchJobItemResponse(
                question_id=9,
                eval_result_id=99,
                status="correct",
                error=None,
                finished_at=datetime(2026, 4, 15, 10, 2, tzinfo=UTC),
            ),
            EvaluationBatchJobItemResponse(
                question_id=10,
                eval_result_id=None,
                status="running",
                error=None,
                finished_at=None,
            ),
            EvaluationBatchJobItemResponse(
                question_id=11,
                eval_result_id=None,
                status="pending",
                error=None,
                finished_at=None,
            ),
        ],
    )


def test_list_batch_jobs_route_returns_jobs(monkeypatch) -> None:
    def fake_list_batch_jobs() -> list[EvaluationBatchJobSummaryResponse]:
        return [build_batch_job_response()]

    monkeypatch.setattr("app.api.routes.evaluations.list_batch_jobs", fake_list_batch_jobs)

    response = client.get("/api/v1/evaluations/batch-jobs")

    body = response.json()
    assert response.status_code == 200
    assert body[0]["job_id"] == "job-1"
    assert body[0]["status"] == "running"


def test_create_batch_job_route_returns_accepted_job(monkeypatch) -> None:
    def fake_create_batch_job(session, payload) -> EvaluationBatchJobResponse:
        assert payload.model_id == 7
        assert payload.execution_mode == "generate_and_judge"
        assert payload.selection_mode == "pending_limit"
        return build_batch_job_response()

    monkeypatch.setattr("app.api.routes.evaluations.create_batch_job", fake_create_batch_job)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.post(
            "/api/v1/evaluations/batch-jobs",
            json={
                "model_id": 7,
                "attempt": 1,
                "execution_mode": "generate_and_judge",
                "selection_mode": "pending_limit",
                "limit": 20,
                "persist_result": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["job_id"] == "job-1"


def test_cancel_batch_job_route_returns_updated_job(monkeypatch) -> None:
    def fake_cancel_batch_job(job_id: str) -> EvaluationBatchJobResponse:
        assert job_id == "job-1"
        response = build_batch_job_response()
        response.status = "cancelled"
        return response

    monkeypatch.setattr("app.api.routes.evaluations.cancel_batch_job", fake_cancel_batch_job)

    response = client.post("/api/v1/evaluations/batch-jobs/job-1/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
