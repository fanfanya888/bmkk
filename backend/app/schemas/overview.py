from __future__ import annotations

from pydantic import BaseModel


class QuestionStatsResponse(BaseModel):
    total_questions: int
    questions_with_content_images: int
    questions_with_answer_images: int
    questions_with_analysis_images: int


class EvaluationStatsResponse(BaseModel):
    total_eval_rows: int
    attempt_1_completed: int
    attempt_2_completed: int
    attempt_3_completed: int
