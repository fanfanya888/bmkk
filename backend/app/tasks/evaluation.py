from __future__ import annotations

from app.celery_app import celery_app
from app.db.session import get_sync_session
from app.schemas.evaluation import EvaluationRunRequest
from app.services.evaluation_service import run_evaluation


@celery_app.task(name="evaluation.run_placeholder")
def run_evaluation_placeholder() -> dict[str, str]:
    return {"status": "pending", "message": "evaluation task is not implemented yet"}


@celery_app.task(name="evaluation.run_once")
def run_evaluation_once_task(
    question_id: int,
    model_id: int,
    attempt: int = 1,
) -> dict[str, object]:
    with get_sync_session() as session:
        result = run_evaluation(
            session,
            EvaluationRunRequest(
                question_id=question_id,
                model_id=model_id,
                attempt=attempt,
                persist_result=True,
            ),
        )
    return result.model_dump(mode="json")
