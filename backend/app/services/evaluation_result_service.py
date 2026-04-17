from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import EvalModel, EvalResult, Question
from app.schemas.evaluation import (
    EvaluationResultAttemptRead,
    EvaluationResultClearRequest,
    EvaluationResultListResponse,
    EvaluationResultModelRead,
    EvaluationResultOverrideRequest,
    EvaluationResultQueryParams,
    EvaluationResultQuestionRead,
    EvaluationResultRowResponse,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class EvaluationResultQueryError(ValueError):
    """Raised when evaluation-result query parameters are invalid."""


class EvaluationResultRowNotFoundError(LookupError):
    """Raised when the requested eval_results row does not exist."""


def _normalize_image_paths(raw_paths: list[Any]) -> list[str]:
    normalized_paths: list[str] = []
    for raw_path in raw_paths:
        path = Path(str(raw_path))
        if path.is_absolute():
            try:
                normalized_paths.append(str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
            except ValueError:
                normalized_paths.append(str(path).replace("\\", "/"))
        else:
            normalized_paths.append(str(path).replace("\\", "/"))
    return normalized_paths


def _to_attempt_read(row: EvalResult, attempt: int) -> EvaluationResultAttemptRead:
    judge_result = getattr(row, f"attempt_{attempt}_result")
    result_override = getattr(row, f"attempt_{attempt}_result_override")
    effective_result = result_override if result_override is not None else judge_result
    overridden_at = getattr(row, f"attempt_{attempt}_result_overridden_at")
    response_text = getattr(row, f"attempt_{attempt}_response_text")
    judge_feedback = getattr(row, f"attempt_{attempt}_judge_feedback")
    error = getattr(row, f"attempt_{attempt}_error")
    finished_at = getattr(row, f"attempt_{attempt}_finished_at")

    if effective_result == 1:
        status = "correct"
    elif effective_result == 0:
        status = "incorrect"
    elif error and result_override is None:
        status = "error"
    elif response_text:
        status = "generated"
    else:
        status = "pending"

    return EvaluationResultAttemptRead(
        attempt=attempt,
        status=status,
        result=effective_result,
        judge_result=judge_result,
        result_override=result_override,
        is_result_overridden=result_override is not None,
        result_overridden_at=overridden_at,
        response_text=response_text,
        judge_feedback=judge_feedback,
        error=error,
        finished_at=finished_at,
        has_response_text=bool(response_text),
        has_judge_feedback=bool(judge_feedback),
    )


def _to_question_read(question: Question) -> EvaluationResultQuestionRead:
    return EvaluationResultQuestionRead(
        question_id=question.question_id,
        parent_id=question.parent_id,
        subject=question.subject,
        stage=question.stage,
        grade=question.grade,
        textbook_chapter=question.textbook_chapter,
        knowledge_level_1=question.knowledge_level_1,
        knowledge_level_2=question.knowledge_level_2,
        knowledge_level_3=question.knowledge_level_3,
        question_type=question.question_type,
        difficulty=question.difficulty,
        content_text=question.content_text,
        content_image_paths=_normalize_image_paths(question.content_images),
        answer_text=question.answer_text,
        answer_image_paths=_normalize_image_paths(question.answer_images),
        analysis_text=question.analysis_text,
        analysis_image_paths=_normalize_image_paths(question.analysis_images),
    )


def _to_model_read(model: EvalModel) -> EvaluationResultModelRead:
    return EvaluationResultModelRead(
        model_id=model.model_id,
        model_name=model.model_name,
        api_style=model.api_style,
        api_model=model.api_model,
        release_date=model.release_date,
        is_active=model.is_active,
    )


def _to_result_row(row: EvalResult, question: Question, model: EvalModel) -> EvaluationResultRowResponse:
    attempt_1 = _to_attempt_read(row, 1)
    attempt_2 = _to_attempt_read(row, 2)
    attempt_3 = _to_attempt_read(row, 3)
    finished_candidates = [
        attempt_1.finished_at,
        attempt_2.finished_at,
        attempt_3.finished_at,
    ]
    latest_finished_at = max(
        (candidate for candidate in finished_candidates if candidate is not None),
        default=None,
    )

    return EvaluationResultRowResponse(
        eval_result_id=row.eval_result_id,
        question=_to_question_read(question),
        model=_to_model_read(model),
        attempt_1=attempt_1,
        attempt_2=attempt_2,
        attempt_3=attempt_3,
        latest_finished_at=latest_finished_at,
        has_any_data=any(
            [
                attempt_1.has_response_text,
                attempt_1.has_judge_feedback,
                attempt_1.error is not None,
                attempt_1.result is not None,
                attempt_2.has_response_text,
                attempt_2.has_judge_feedback,
                attempt_2.error is not None,
                attempt_2.result is not None,
                attempt_3.has_response_text,
                attempt_3.has_judge_feedback,
                attempt_3.error is not None,
                attempt_3.result is not None,
            ]
        ),
    )


def _build_has_any_data_filters() -> list[Any]:
    filters: list[Any] = []
    for attempt in (1, 2, 3):
        filters.extend(
            [
                getattr(EvalResult, f"attempt_{attempt}_result").is_not(None),
                getattr(EvalResult, f"attempt_{attempt}_response_text").is_not(None),
                getattr(EvalResult, f"attempt_{attempt}_judge_feedback").is_not(None),
                getattr(EvalResult, f"attempt_{attempt}_error").is_not(None),
                getattr(EvalResult, f"attempt_{attempt}_finished_at").is_not(None),
            ]
        )
    return filters


def _build_attempt_has_data_filters(attempt: int) -> list[Any]:
    return [
        getattr(EvalResult, f"attempt_{attempt}_result").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_result_override").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_response_text").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_judge_feedback").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_error").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_finished_at").is_not(None),
    ]


def _build_attempt_status_filter(attempt: int, status: str) -> Any:
    result_col = getattr(EvalResult, f"attempt_{attempt}_result")
    result_override_col = getattr(EvalResult, f"attempt_{attempt}_result_override")
    response_col = getattr(EvalResult, f"attempt_{attempt}_response_text")
    judge_col = getattr(EvalResult, f"attempt_{attempt}_judge_feedback")
    error_col = getattr(EvalResult, f"attempt_{attempt}_error")
    finished_col = getattr(EvalResult, f"attempt_{attempt}_finished_at")
    effective_result = func.coalesce(result_override_col, result_col)

    if status == "pending":
        return (
            effective_result.is_(None)
            & response_col.is_(None)
            & judge_col.is_(None)
            & error_col.is_(None)
            & finished_col.is_(None)
        )
    if status == "generated":
        return response_col.is_not(None) & effective_result.is_(None) & error_col.is_(None)
    if status == "correct":
        return effective_result == 1
    if status == "incorrect":
        return effective_result == 0
    if status == "error":
        return error_col.is_not(None) & result_override_col.is_(None)

    raise EvaluationResultQueryError(f"unsupported attempt_status: {status}")


def _parse_attempt_statuses(raw_statuses: str | None) -> list[str]:
    if not raw_statuses:
        return []

    statuses = [item.strip() for item in raw_statuses.split(",") if item.strip()]
    allowed_statuses = {"pending", "generated", "correct", "incorrect", "error"}
    invalid_statuses = [status for status in statuses if status not in allowed_statuses]
    if invalid_statuses:
        raise EvaluationResultQueryError(
            f"unsupported attempt_status values: {', '.join(invalid_statuses)}"
        )
    return list(dict.fromkeys(statuses))


def list_evaluation_results(
    session: Session,
    params: EvaluationResultQueryParams,
) -> EvaluationResultListResponse:
    if (
        params.question_id_start is not None
        and params.question_id_end is not None
        and params.question_id_start > params.question_id_end
    ):
        raise EvaluationResultQueryError("question_id_start cannot be greater than question_id_end")

    attempt_statuses = _parse_attempt_statuses(params.attempt_statuses)

    stmt = (
        select(EvalResult, Question, EvalModel)
        .join(Question, EvalResult.question_id == Question.question_id)
        .join(EvalModel, EvalResult.model_id == EvalModel.model_id)
    )

    if params.model_id is not None:
        stmt = stmt.where(EvalResult.model_id == params.model_id)
    if params.question_id is not None:
        stmt = stmt.where(EvalResult.question_id == params.question_id)
    if params.question_id_start is not None:
        stmt = stmt.where(EvalResult.question_id >= params.question_id_start)
    if params.question_id_end is not None:
        stmt = stmt.where(EvalResult.question_id <= params.question_id_end)
    if params.only_with_data:
        stmt = stmt.where(or_(*_build_attempt_has_data_filters(params.attempt)))
    if attempt_statuses:
        stmt = stmt.where(
            or_(*[_build_attempt_status_filter(params.attempt, status) for status in attempt_statuses])
        )

    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0

    rows = session.execute(
        stmt.order_by(
            EvalResult.question_id.asc(),
            EvalModel.sort_order.asc(),
            EvalModel.model_id.asc(),
        )
        .limit(params.limit)
        .offset(params.offset)
    ).all()

    return EvaluationResultListResponse(
        total=total,
        limit=params.limit,
        offset=params.offset,
        items=[_to_result_row(row, question, model) for row, question, model in rows],
    )


def clear_evaluation_result_attempt(
    session: Session,
    eval_result_id: int,
    payload: EvaluationResultClearRequest,
) -> EvaluationResultRowResponse:
    row = session.get(EvalResult, eval_result_id)
    if row is None:
        raise EvaluationResultRowNotFoundError(f"eval_result {eval_result_id} does not exist")

    if payload.scope == "generation_data":
        suffixes = [
            "result",
            "result_override",
            "result_overridden_at",
            "response_text",
            "judge_feedback",
            "error",
            "finished_at",
        ]
    else:
        suffixes = [
            "result",
            "result_override",
            "result_overridden_at",
            "judge_feedback",
            "error",
            "finished_at",
        ]

    for suffix in suffixes:
        setattr(row, f"attempt_{payload.attempt}_{suffix}", None)

    session.commit()
    session.refresh(row)

    return _to_result_row(row, row.question, row.model)


def override_evaluation_result_attempt(
    session: Session,
    eval_result_id: int,
    payload: EvaluationResultOverrideRequest,
) -> EvaluationResultRowResponse:
    row = session.get(EvalResult, eval_result_id)
    if row is None:
        raise EvaluationResultRowNotFoundError(f"eval_result {eval_result_id} does not exist")

    setattr(row, f"attempt_{payload.attempt}_result_override", payload.result)
    setattr(
        row,
        f"attempt_{payload.attempt}_result_overridden_at",
        datetime.now(UTC) if payload.result is not None else None,
    )

    session.commit()
    session.refresh(row)

    return _to_result_row(row, row.question, row.model)
