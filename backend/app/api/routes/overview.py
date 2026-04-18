from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import db_session_dependency
from app.schemas.overview import (
    EvaluationLeaderboardResponse,
    EvaluationStatsResponse,
    QuestionStatsResponse,
)
from app.services.overview_service import (
    get_evaluation_leaderboard,
    get_evaluation_stats,
    get_question_stats,
)


router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("/questions", response_model=QuestionStatsResponse)
def overview_questions(session: Session = Depends(db_session_dependency)) -> QuestionStatsResponse:
    return get_question_stats(session)


@router.get("/evaluations", response_model=EvaluationStatsResponse)
def overview_evaluations(
    session: Session = Depends(db_session_dependency),
) -> EvaluationStatsResponse:
    return get_evaluation_stats(session)


@router.get("/evaluation-leaderboard", response_model=EvaluationLeaderboardResponse)
def overview_evaluation_leaderboard(
    session: Session = Depends(db_session_dependency),
) -> EvaluationLeaderboardResponse:
    return get_evaluation_leaderboard(session)
