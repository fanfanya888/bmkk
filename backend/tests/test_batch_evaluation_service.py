from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.evaluation import EvaluationRunResponse
from app.services import batch_evaluation_service
from app.services.batch_evaluation_service import BatchJobItemState, BatchJobState


def _build_result(*, question_id: int, result: int | None, error: str | None = None) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        eval_result_id=question_id * 10,
        question_id=question_id,
        model_id=7,
        model_name="Hunyuan",
        attempt=1,
        attempt_result=result,
        response_text="模型回复",
        judge_feedback=None,
        error=error,
        finished_at=datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
    )


def test_run_batch_job_continues_after_single_item_exception(monkeypatch) -> None:
    job = BatchJobState(
        job_id="job-test",
        model_id=7,
        model_name="Hunyuan",
        attempt=1,
        execution_mode="generate_and_judge",
        selection_mode="pending_limit",
        persist_result=True,
        request_timeout_seconds=60.0,
        force=False,
        items=[
            BatchJobItemState(question_id=1),
            BatchJobItemState(question_id=2),
            BatchJobItemState(question_id=3),
        ],
    )

    monkeypatch.setitem(batch_evaluation_service._jobs, job.job_id, job)

    def fake_execute_job_item(current_job: BatchJobState, question_id: int) -> EvaluationRunResponse:
        assert current_job.job_id == "job-test"
        if question_id == 2:
            raise RuntimeError("judge provider temporary failure")
        return _build_result(question_id=question_id, result=1)

    monkeypatch.setattr(batch_evaluation_service, "_execute_job_item", fake_execute_job_item)

    try:
        batch_evaluation_service._run_batch_job(job.job_id)
    finally:
        batch_evaluation_service._jobs.pop(job.job_id, None)

    assert job.status == "completed"
    assert job.completed_questions == 3
    assert job.correct_count == 2
    assert job.error_count == 1
    assert job.job_error is None
    assert job.items[0].status == "correct"
    assert job.items[1].status == "error"
    assert job.items[1].error == "judge provider temporary failure"
    assert job.items[2].status == "correct"
