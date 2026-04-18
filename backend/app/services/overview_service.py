from __future__ import annotations

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models import EvalResult, Question
from app.models.eval_model import EvalModel
from app.schemas.overview import (
    EvaluationLeaderboardResponse,
    EvaluationLeaderboardRowResponse,
    EvaluationStatsResponse,
    QuestionStatsResponse,
)


def get_question_stats(session: Session) -> QuestionStatsResponse:
    stmt = select(
        func.count().label("total_questions"),
        func.count().filter(func.jsonb_array_length(Question.content_images) > 0).label(
            "questions_with_content_images"
        ),
        func.count().filter(func.jsonb_array_length(Question.answer_images) > 0).label(
            "questions_with_answer_images"
        ),
        func.count().filter(func.jsonb_array_length(Question.analysis_images) > 0).label(
            "questions_with_analysis_images"
        ),
    )
    row = session.execute(stmt).one()
    return QuestionStatsResponse(
        total_questions=row.total_questions,
        questions_with_content_images=row.questions_with_content_images,
        questions_with_answer_images=row.questions_with_answer_images,
        questions_with_analysis_images=row.questions_with_analysis_images,
    )


def get_evaluation_stats(session: Session) -> EvaluationStatsResponse:
    stmt = select(
        func.count().label("total_eval_rows"),
        func.count().filter(EvalResult.attempt_1_result.is_not(None)).label("attempt_1_completed"),
        func.count().filter(EvalResult.attempt_2_result.is_not(None)).label("attempt_2_completed"),
        func.count().filter(EvalResult.attempt_3_result.is_not(None)).label("attempt_3_completed"),
    )
    row = session.execute(stmt).one()
    return EvaluationStatsResponse(
        total_eval_rows=row.total_eval_rows,
        attempt_1_completed=row.attempt_1_completed,
        attempt_2_completed=row.attempt_2_completed,
        attempt_3_completed=row.attempt_3_completed,
    )


def _attempt_effective_result(attempt: int):
    return func.coalesce(
        getattr(EvalResult, f"attempt_{attempt}_result_override"),
        getattr(EvalResult, f"attempt_{attempt}_result"),
    )


def _attempt_has_data(attempt: int):
    return or_(
        getattr(EvalResult, f"attempt_{attempt}_result").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_result_override").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_response_text").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_judge_feedback").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_error").is_not(None),
        getattr(EvalResult, f"attempt_{attempt}_finished_at").is_not(None),
    )


def _attempt_not_correct(result_expression):
    return or_(result_expression.is_(None), result_expression != 1)


def get_evaluation_leaderboard(session: Session) -> EvaluationLeaderboardResponse:
    attempt_1_result = _attempt_effective_result(1)
    attempt_2_result = _attempt_effective_result(2)
    attempt_3_result = _attempt_effective_result(3)
    attempt_1_has_data = _attempt_has_data(1)
    attempt_2_has_data = _attempt_has_data(2)
    attempt_3_has_data = _attempt_has_data(3)
    latest_finished_at = func.max(
        case(
            (
                EvalResult.attempt_3_finished_at.is_not(None),
                EvalResult.attempt_3_finished_at,
            ),
            (
                EvalResult.attempt_2_finished_at.is_not(None),
                EvalResult.attempt_2_finished_at,
            ),
            else_=EvalResult.attempt_1_finished_at,
        )
    )

    stmt = (
        select(
            EvalModel.model_id,
            EvalModel.model_name,
            EvalModel.api_style,
            EvalModel.api_model,
            EvalModel.release_date,
            EvalModel.is_active,
            EvalModel.sort_order,
            func.count(EvalResult.eval_result_id).label("sample_count"),
            func.count().filter(attempt_1_has_data).label("attempt_1_run_count"),
            func.count().filter(attempt_1_result == 1).label("attempt_1_correct_count"),
            func.count().filter(EvalResult.attempt_1_error.is_not(None)).label("attempt_1_error_count"),
            func.count().filter(attempt_2_has_data).label("attempt_2_run_count"),
            func.count()
            .filter(_attempt_not_correct(attempt_1_result))
            .filter(attempt_2_result == 1)
            .label("attempt_2_incremental_correct_count"),
            func.count()
            .filter(or_(attempt_1_result == 1, attempt_2_result == 1))
            .label("attempt_2_cumulative_correct_count"),
            func.count().filter(attempt_3_has_data).label("attempt_3_run_count"),
            func.count()
            .filter(_attempt_not_correct(attempt_1_result))
            .filter(_attempt_not_correct(attempt_2_result))
            .filter(attempt_3_result == 1)
            .label("attempt_3_incremental_correct_count"),
            func.count()
            .filter(or_(attempt_1_result == 1, attempt_2_result == 1, attempt_3_result == 1))
            .label("attempt_3_cumulative_correct_count"),
            latest_finished_at.label("latest_finished_at"),
        )
        .select_from(EvalModel)
        .outerjoin(EvalResult, EvalResult.model_id == EvalModel.model_id)
        .group_by(
            EvalModel.model_id,
            EvalModel.model_name,
            EvalModel.api_style,
            EvalModel.api_model,
            EvalModel.release_date,
            EvalModel.is_active,
            EvalModel.sort_order,
        )
        .order_by(EvalModel.sort_order.asc(), EvalModel.model_id.asc())
    )

    rows = session.execute(stmt).all()
    return EvaluationLeaderboardResponse(
        items=[
            EvaluationLeaderboardRowResponse(
                model_id=row.model_id,
                model_name=row.model_name,
                api_style=row.api_style,
                api_model=row.api_model,
                release_date=row.release_date,
                is_active=row.is_active,
                sort_order=row.sort_order,
                sample_count=row.sample_count,
                attempt_1_run_count=row.attempt_1_run_count,
                attempt_1_correct_count=row.attempt_1_correct_count,
                attempt_1_error_count=row.attempt_1_error_count,
                attempt_2_run_count=row.attempt_2_run_count,
                attempt_2_incremental_correct_count=row.attempt_2_incremental_correct_count,
                attempt_2_cumulative_correct_count=row.attempt_2_cumulative_correct_count,
                attempt_3_run_count=row.attempt_3_run_count,
                attempt_3_incremental_correct_count=row.attempt_3_incremental_correct_count,
                attempt_3_cumulative_correct_count=row.attempt_3_cumulative_correct_count,
                latest_finished_at=row.latest_finished_at,
            )
            for row in rows
        ]
    )
