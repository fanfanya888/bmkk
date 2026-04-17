from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models import EvalResult
from app.schemas.evaluation import (
    BatchItemStatus,
    BatchJobStatus,
    BatchSelectionMode,
    EvaluationExecutionMode,
    EvaluationBatchJobCreateRequest,
    EvaluationBatchJobItemResponse,
    EvaluationBatchJobResponse,
    EvaluationBatchJobSummaryResponse,
    EvaluationGenerateRequest,
    EvaluationJudgeRequest,
    EvaluationRunRequest,
    EvaluationRunResponse,
)
from app.services.evaluation_service import generate_evaluation, judge_evaluation, run_evaluation
from app.services.model_service import (
    ModelConfigurationError,
    ModelNotFoundError,
    get_model_runtime_config,
)


TERMINAL_BATCH_JOB_STATUSES = {"completed", "cancelled", "failed"}
RUNNING_BATCH_JOB_STATUSES = {"queued", "running"}
MAX_BATCH_JOBS = 20
logger = logging.getLogger("uvicorn.error")


class BatchJobNotFoundError(LookupError):
    """Raised when the requested batch job does not exist."""


class BatchJobSelectionError(ValueError):
    """Raised when batch-job selection parameters are invalid."""


@dataclass(slots=True)
class BatchJobItemState:
    question_id: int
    eval_result_id: int | None = None
    status: BatchItemStatus = "pending"
    error: str | None = None
    finished_at: datetime | None = None


@dataclass(slots=True)
class BatchJobState:
    job_id: str
    model_id: int
    model_name: str
    attempt: int
    execution_mode: EvaluationExecutionMode
    selection_mode: BatchSelectionMode
    persist_result: bool
    request_timeout_seconds: float | None
    force: bool
    items: list[BatchJobItemState]
    status: BatchJobStatus = "queued"
    completed_questions: int = 0
    current_question_id: int | None = None
    generated_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    error_count: int = 0
    unknown_count: int = 0
    cancelled_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    job_error: str | None = None
    cancel_requested: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def total_questions(self) -> int:
        return len(self.items)


_jobs: dict[str, BatchJobState] = {}
_jobs_lock = threading.Lock()


def _build_pending_filters(payload: EvaluationBatchJobCreateRequest):
    attempt_finished_at = getattr(EvalResult, f"attempt_{payload.attempt}_finished_at")
    attempt_response_text = getattr(EvalResult, f"attempt_{payload.attempt}_response_text")
    attempt_result = getattr(EvalResult, f"attempt_{payload.attempt}_result")

    if payload.execution_mode == "generate_only":
        return [attempt_response_text.is_(None)]
    if payload.execution_mode == "judge_only":
        return [
            attempt_response_text.is_not(None),
            attempt_result.is_(None),
        ]
    return [attempt_result.is_(None)]


def _resolve_question_ids(session: Session, payload: EvaluationBatchJobCreateRequest) -> list[int]:
    selection_mode = payload.selection_mode
    pending_filters = _build_pending_filters(payload)

    if selection_mode == "pending_all":
        stmt = (
            select(EvalResult.question_id)
            .where(
                EvalResult.model_id == payload.model_id,
                *pending_filters,
            )
            .order_by(EvalResult.question_id.asc())
        )
        return list(session.scalars(stmt).all())

    if selection_mode == "pending_limit":
        limit = payload.limit
        if limit is None:
            raise BatchJobSelectionError("limit is required when selection_mode=pending_limit")
        stmt = (
            select(EvalResult.question_id)
            .where(
                EvalResult.model_id == payload.model_id,
                *pending_filters,
            )
            .order_by(EvalResult.question_id.asc())
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    if selection_mode == "range":
        if payload.question_id_start is None or payload.question_id_end is None:
            raise BatchJobSelectionError(
                "question_id_start and question_id_end are required when selection_mode=range"
            )
        if payload.question_id_start > payload.question_id_end:
            raise BatchJobSelectionError("question_id_start cannot be greater than question_id_end")

        stmt = (
            select(EvalResult.question_id)
            .where(
                EvalResult.model_id == payload.model_id,
                EvalResult.question_id >= payload.question_id_start,
                EvalResult.question_id <= payload.question_id_end,
            )
            .order_by(EvalResult.question_id.asc())
        )
        if not payload.force:
            stmt = stmt.where(*pending_filters)
        return list(session.scalars(stmt).all())

    if selection_mode == "manual":
        if not payload.question_ids:
            raise BatchJobSelectionError("question_ids are required when selection_mode=manual")

        ordered_ids = list(dict.fromkeys(payload.question_ids))
        stmt = select(EvalResult.question_id).where(
            EvalResult.model_id == payload.model_id,
            EvalResult.question_id.in_(ordered_ids),
        )
        if not payload.force:
            stmt = stmt.where(*pending_filters)
        available_ids = set(session.scalars(stmt).all())
        return [question_id for question_id in ordered_ids if question_id in available_ids]

    raise BatchJobSelectionError(f"unsupported selection_mode: {selection_mode}")


def _job_to_summary(job: BatchJobState) -> EvaluationBatchJobSummaryResponse:
    with job.lock:
        return EvaluationBatchJobSummaryResponse(
            job_id=job.job_id,
            model_id=job.model_id,
            model_name=job.model_name,
            attempt=job.attempt,
            execution_mode=job.execution_mode,
            selection_mode=job.selection_mode,
            persist_result=job.persist_result,
            request_timeout_seconds=job.request_timeout_seconds,
            force=job.force,
            status=job.status,
            total_questions=job.total_questions,
            completed_questions=job.completed_questions,
            current_question_id=job.current_question_id,
            generated_count=job.generated_count,
            correct_count=job.correct_count,
            incorrect_count=job.incorrect_count,
            error_count=job.error_count,
            unknown_count=job.unknown_count,
            cancelled_count=job.cancelled_count,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            job_error=job.job_error,
        )


def _job_to_detail(job: BatchJobState) -> EvaluationBatchJobResponse:
    with job.lock:
        return EvaluationBatchJobResponse(
            job_id=job.job_id,
            model_id=job.model_id,
            model_name=job.model_name,
            attempt=job.attempt,
            execution_mode=job.execution_mode,
            selection_mode=job.selection_mode,
            persist_result=job.persist_result,
            request_timeout_seconds=job.request_timeout_seconds,
            force=job.force,
            status=job.status,
            total_questions=job.total_questions,
            completed_questions=job.completed_questions,
            current_question_id=job.current_question_id,
            generated_count=job.generated_count,
            correct_count=job.correct_count,
            incorrect_count=job.incorrect_count,
            error_count=job.error_count,
            unknown_count=job.unknown_count,
            cancelled_count=job.cancelled_count,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            job_error=job.job_error,
            items=[
                EvaluationBatchJobItemResponse(
                    question_id=item.question_id,
                    eval_result_id=item.eval_result_id,
                    status=item.status,
                    error=item.error,
                    finished_at=item.finished_at,
                )
                for item in job.items
            ],
        )


def _get_job_or_raise(job_id: str) -> BatchJobState:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise BatchJobNotFoundError(f"batch job {job_id} does not exist")
    return job


def _trim_jobs() -> None:
    with _jobs_lock:
        removable_ids = [
            job_id
            for job_id, job in sorted(
                _jobs.items(),
                key=lambda item: item[1].created_at,
            )
            if job.status in TERMINAL_BATCH_JOB_STATUSES
        ]
        while len(_jobs) > MAX_BATCH_JOBS and removable_ids:
            _jobs.pop(removable_ids.pop(0), None)


def list_batch_jobs() -> list[EvaluationBatchJobSummaryResponse]:
    with _jobs_lock:
        jobs = list(_jobs.values())
    jobs.sort(key=lambda job: job.created_at, reverse=True)
    return [_job_to_summary(job) for job in jobs]


def get_batch_job(job_id: str) -> EvaluationBatchJobResponse:
    return _job_to_detail(_get_job_or_raise(job_id))


def cancel_batch_job(job_id: str) -> EvaluationBatchJobResponse:
    job = _get_job_or_raise(job_id)
    with job.lock:
        if job.status in TERMINAL_BATCH_JOB_STATUSES:
            pass
        else:
            job.cancel_requested = True
            logger.info(
                "已请求停止批量任务 job_id=%s status=%s 已完成=%s/%s",
                job.job_id,
                job.status,
                job.completed_questions,
                job.total_questions,
            )
            if job.status == "queued":
                job.status = "cancelled"
                job.finished_at = datetime.now(UTC)
                for item in job.items:
                    if item.status == "pending":
                        item.status = "cancelled"
                        job.cancelled_count += 1
    return _job_to_detail(job)


def create_batch_job(
    session: Session,
    payload: EvaluationBatchJobCreateRequest,
) -> EvaluationBatchJobResponse:
    resolved_model = get_model_runtime_config(session, payload.model_id)
    question_ids = _resolve_question_ids(session, payload)
    if not question_ids:
        raise BatchJobSelectionError("no questions matched the current batch selection")

    job = BatchJobState(
        job_id=uuid4().hex,
        model_id=resolved_model.model_id,
        model_name=resolved_model.model_name,
        attempt=payload.attempt,
        execution_mode=payload.execution_mode,
        selection_mode=payload.selection_mode,
        persist_result=payload.persist_result,
        request_timeout_seconds=payload.request_timeout_seconds,
        force=payload.force,
        items=[BatchJobItemState(question_id=question_id) for question_id in question_ids],
    )

    with _jobs_lock:
        _jobs[job.job_id] = job

    logger.info(
        "已创建批量任务 job_id=%s model_id=%s model_name=%s 执行模式=%s 批量模式=%s 总题数=%s",
        job.job_id,
        job.model_id,
        job.model_name,
        job.execution_mode,
        job.selection_mode,
        job.total_questions,
    )

    thread = threading.Thread(
        target=_run_batch_job,
        args=(job.job_id,),
        daemon=True,
        name=f"batch-eval-{job.job_id[:8]}",
    )
    thread.start()
    _trim_jobs()
    return _job_to_detail(job)


def _execute_job_item(job: BatchJobState, question_id: int):
    with get_sync_session() as session:
        if job.execution_mode == "generate_only":
            return generate_evaluation(
                session,
                EvaluationGenerateRequest(
                    question_id=question_id,
                    model_id=job.model_id,
                    attempt=job.attempt,
                    persist_result=job.persist_result,
                    request_timeout_seconds=job.request_timeout_seconds,
                ),
            )
        if job.execution_mode == "judge_only":
            return judge_evaluation(
                session,
                EvaluationJudgeRequest(
                    question_id=question_id,
                    model_id=job.model_id,
                    attempt=job.attempt,
                    persist_result=job.persist_result,
                ),
            )
        return run_evaluation(
            session,
            EvaluationRunRequest(
                question_id=question_id,
                model_id=job.model_id,
                attempt=job.attempt,
                persist_result=job.persist_result,
                request_timeout_seconds=job.request_timeout_seconds,
            ),
        )


def _increment_counter(
    job: BatchJobState,
    status: Literal["generated", "correct", "incorrect", "error", "unknown"],
) -> None:
    if status == "generated":
        job.generated_count += 1
    elif status == "correct":
        job.correct_count += 1
    elif status == "incorrect":
        job.incorrect_count += 1
    elif status == "error":
        job.error_count += 1
    else:
        job.unknown_count += 1


def _apply_job_item_result(
    job: BatchJobState,
    item: BatchJobItemState,
    result: EvaluationRunResponse,
) -> None:
    item.eval_result_id = result.eval_result_id
    item.finished_at = result.finished_at
    item.error = result.error
    if result.error:
        item.status = "error"
    elif job.execution_mode == "generate_only":
        item.status = "generated"
    elif result.attempt_result == 1:
        item.status = "correct"
    elif result.attempt_result == 0:
        item.status = "incorrect"
    else:
        item.status = "unknown"
    job.completed_questions += 1
    _increment_counter(job, item.status)


def _apply_job_item_exception(
    job: BatchJobState,
    item: BatchJobItemState,
    exc: Exception,
) -> None:
    item.error = str(exc)
    item.finished_at = datetime.now(UTC)
    item.status = "error"
    job.completed_questions += 1
    _increment_counter(job, item.status)


def _run_batch_job(job_id: str) -> None:
    job = _get_job_or_raise(job_id)

    with job.lock:
        if job.status == "cancelled":
            return
        job.status = "running"
        job.started_at = datetime.now(UTC)
        logger.info(
            "批量任务开始执行 job_id=%s model_name=%s 执行模式=%s 总题数=%s",
            job.job_id,
            job.model_name,
            job.execution_mode,
            job.total_questions,
        )

    try:
        for index, item in enumerate(job.items, start=1):
            with job.lock:
                if job.cancel_requested:
                    break
                job.current_question_id = item.question_id
                item.status = "running"
                logger.info(
                    "批量任务进行中 job_id=%s 进度=%s/%s 当前题号=%s 执行模式=%s",
                    job.job_id,
                    index,
                    job.total_questions,
                    item.question_id,
                    job.execution_mode,
                )

            try:
                result = _execute_job_item(job, item.question_id)
            except Exception as exc:
                with job.lock:
                    _apply_job_item_exception(job, item, exc)
                    logger.exception(
                        "批量任务单题失败 job_id=%s question_id=%s 已完成=%s/%s error=%s",
                        job.job_id,
                        item.question_id,
                        job.completed_questions,
                        job.total_questions,
                        exc,
                    )
                continue

            with job.lock:
                _apply_job_item_result(job, item, result)
                logger.info(
                    "批量任务进度 job_id=%s 已完成=%s/%s question_id=%s 状态=%s 错误=%s",
                    job.job_id,
                    job.completed_questions,
                    job.total_questions,
                    item.question_id,
                    item.status,
                    item.error,
                )

        with job.lock:
            if job.cancel_requested:
                for item in job.items:
                    if item.status == "pending":
                        item.status = "cancelled"
                        job.cancelled_count += 1
                job.status = "cancelled"
                logger.info(
                    "批量任务已取消 job_id=%s 已完成=%s/%s 已生成=%s 正确=%s 不正确=%s 失败=%s 未知=%s 已取消=%s",
                    job.job_id,
                    job.completed_questions,
                    job.total_questions,
                    job.generated_count,
                    job.correct_count,
                    job.incorrect_count,
                    job.error_count,
                    job.unknown_count,
                    job.cancelled_count,
                )
            else:
                job.status = "completed"
                logger.info(
                    "批量任务已完成 job_id=%s 已完成=%s/%s 已生成=%s 正确=%s 不正确=%s 失败=%s 未知=%s 已取消=%s",
                    job.job_id,
                    job.completed_questions,
                    job.total_questions,
                    job.generated_count,
                    job.correct_count,
                    job.incorrect_count,
                    job.error_count,
                    job.unknown_count,
                    job.cancelled_count,
                )
            job.current_question_id = None
            job.finished_at = datetime.now(UTC)
    except Exception as exc:
        with job.lock:
            job.status = "failed"
            job.current_question_id = None
            job.finished_at = datetime.now(UTC)
            job.job_error = str(exc)
            logger.exception(
                "批量任务失败 job_id=%s 已完成=%s/%s error=%s",
                job.job_id,
                job.completed_questions,
                job.total_questions,
                exc,
            )
