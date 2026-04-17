from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.api_styles import APIStyle


class EvaluationPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    question_id: int = Field(gt=0)
    model_id: int = Field(gt=0)


class EvaluationPreviewResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    question_id: int
    model_id: int
    model_name: str
    model_is_active: bool
    model_is_configured: bool
    prompt_text: str
    content_image_paths: list[str]


class EvaluationPayloadContentPreview(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    type: str
    text: str | None = None
    image_path: str | None = None
    mime_type: str | None = None
    image_url_preview: str | None = None
    image_url_length: int | None = None


class EvaluationPayloadMessagePreview(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    role: str
    content: list[EvaluationPayloadContentPreview]


class EvaluationPayloadPreviewResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    question_id: int
    model_id: int
    model_name: str
    api_style: APIStyle
    api_model: str
    request_url: str
    payload: dict[str, Any]


class EvaluationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    question_id: int = Field(gt=0)
    model_id: int = Field(gt=0)
    attempt: int = Field(default=1, ge=1, le=3)
    persist_result: bool = True
    request_timeout_seconds: float | None = Field(default=None, gt=0)


class EvaluationRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    eval_result_id: int
    question_id: int
    model_id: int
    model_name: str
    attempt: int
    attempt_result: int | None
    response_text: str | None
    judge_feedback: str | None
    error: str | None
    finished_at: datetime


EvaluationExecutionMode = Literal["generate_only", "judge_only", "generate_and_judge"]
EvaluationRunStatus = Literal["correct", "incorrect", "error", "unknown"]
EvaluationGenerateStatus = Literal["generated", "error"]


class EvaluationGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    question_id: int = Field(gt=0)
    model_id: int = Field(gt=0)
    attempt: int = Field(default=1, ge=1, le=3)
    persist_result: bool = True
    request_timeout_seconds: float | None = Field(default=None, gt=0)


class EvaluationJudgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    question_id: int = Field(gt=0)
    model_id: int = Field(gt=0)
    attempt: int = Field(default=1, ge=1, le=3)
    persist_result: bool = True


class EvaluationGenerateSummaryResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    eval_result_id: int
    question_id: int
    model_id: int
    model_name: str
    attempt: int
    status: EvaluationGenerateStatus
    error: str | None
    finished_at: datetime


class EvaluationJudgeSummaryResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    eval_result_id: int
    question_id: int
    model_id: int
    model_name: str
    attempt: int
    status: EvaluationRunStatus
    error: str | None
    finished_at: datetime


class EvaluationRunSummaryResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    eval_result_id: int
    question_id: int
    model_id: int
    model_name: str
    attempt: int
    status: EvaluationRunStatus
    error: str | None
    finished_at: datetime


BatchSelectionMode = Literal["pending_all", "pending_limit", "range", "manual"]
BatchJobStatus = Literal["queued", "running", "completed", "cancelled", "failed"]
BatchItemStatus = Literal[
    "pending",
    "running",
    "generated",
    "correct",
    "incorrect",
    "error",
    "unknown",
    "cancelled",
]


class EvaluationBatchJobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_id: int = Field(gt=0)
    attempt: int = Field(default=1, ge=1, le=3)
    persist_result: bool = True
    request_timeout_seconds: float | None = Field(default=None, gt=0)
    execution_mode: EvaluationExecutionMode = "generate_and_judge"
    selection_mode: BatchSelectionMode = "pending_limit"
    limit: int | None = Field(default=20, gt=0)
    question_id_start: int | None = Field(default=None, gt=0)
    question_id_end: int | None = Field(default=None, gt=0)
    question_ids: list[int] | None = None
    force: bool = False


class EvaluationBatchJobItemResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    question_id: int
    eval_result_id: int | None
    status: BatchItemStatus
    error: str | None
    finished_at: datetime | None


class EvaluationBatchJobSummaryResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: str
    model_id: int
    model_name: str
    attempt: int
    execution_mode: EvaluationExecutionMode
    selection_mode: BatchSelectionMode
    persist_result: bool
    request_timeout_seconds: float | None
    force: bool
    status: BatchJobStatus
    total_questions: int
    completed_questions: int
    current_question_id: int | None
    generated_count: int
    correct_count: int
    incorrect_count: int
    error_count: int
    unknown_count: int
    cancelled_count: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    job_error: str | None


class EvaluationBatchJobResponse(EvaluationBatchJobSummaryResponse):
    model_config = ConfigDict(protected_namespaces=())

    items: list[EvaluationBatchJobItemResponse]


EvaluationResultAttemptStatus = Literal["pending", "generated", "correct", "incorrect", "error"]
EvaluationResultClearScope = Literal["generation_data", "judge_data"]


class EvaluationResultAttemptRead(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    attempt: int
    status: EvaluationResultAttemptStatus
    result: int | None
    judge_result: int | None
    result_override: int | None
    is_result_overridden: bool
    result_overridden_at: datetime | None
    response_text: str | None
    judge_feedback: str | None
    error: str | None
    finished_at: datetime | None
    has_response_text: bool
    has_judge_feedback: bool


class EvaluationResultQuestionRead(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    question_id: int
    parent_id: str
    subject: str
    stage: str
    grade: str
    textbook_chapter: str
    knowledge_level_1: str
    knowledge_level_2: str
    knowledge_level_3: str
    question_type: str
    difficulty: str
    content_text: str
    content_image_paths: list[str]
    answer_text: str
    answer_image_paths: list[str]
    analysis_text: str
    analysis_image_paths: list[str]


class EvaluationResultModelRead(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    model_name: str
    api_style: APIStyle
    api_model: str
    release_date: date | None
    is_active: bool


class EvaluationResultRowResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    eval_result_id: int
    question: EvaluationResultQuestionRead
    model: EvaluationResultModelRead
    attempt_1: EvaluationResultAttemptRead
    attempt_2: EvaluationResultAttemptRead
    attempt_3: EvaluationResultAttemptRead
    latest_finished_at: datetime | None
    has_any_data: bool


class EvaluationResultListResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    total: int
    limit: int
    offset: int
    items: list[EvaluationResultRowResponse]


class EvaluationResultQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_id: int | None = Field(default=None, gt=0)
    question_id: int | None = Field(default=None, gt=0)
    question_id_start: int | None = Field(default=None, gt=0)
    question_id_end: int | None = Field(default=None, gt=0)
    attempt: int = Field(default=1, ge=1, le=3)
    attempt_statuses: str | None = None
    only_with_data: bool = True
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class EvaluationResultClearRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    attempt: int = Field(ge=1, le=3)
    scope: EvaluationResultClearScope


class EvaluationResultOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    attempt: int = Field(ge=1, le=3)
    result: Literal[0, 1] | None = None
