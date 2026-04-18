from __future__ import annotations

from datetime import date
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.api_styles import APIStyle


class QuestionStatsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    total_questions: int
    questions_with_content_images: int
    questions_with_answer_images: int
    questions_with_analysis_images: int


class EvaluationStatsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    total_eval_rows: int
    attempt_1_completed: int
    attempt_2_completed: int
    attempt_3_completed: int


class EvaluationLeaderboardRowResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    model_name: str
    api_style: APIStyle
    api_model: str
    release_date: date | None
    is_active: bool
    sort_order: int
    sample_count: int
    attempt_1_run_count: int
    attempt_1_correct_count: int
    attempt_1_error_count: int
    attempt_2_run_count: int
    attempt_2_incremental_correct_count: int
    attempt_2_cumulative_correct_count: int
    attempt_3_run_count: int
    attempt_3_incremental_correct_count: int
    attempt_3_cumulative_correct_count: int
    latest_finished_at: datetime | None


class EvaluationLeaderboardResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    items: list[EvaluationLeaderboardRowResponse]
