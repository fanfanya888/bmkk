from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EvalResult, Question
from app.schemas.overview import EvaluationStatsResponse, QuestionStatsResponse


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
