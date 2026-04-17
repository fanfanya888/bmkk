from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import db_session_dependency
from app.schemas.evaluation import (
    EvaluationBatchJobCreateRequest,
    EvaluationBatchJobResponse,
    EvaluationBatchJobSummaryResponse,
    EvaluationResultClearRequest,
    EvaluationResultListResponse,
    EvaluationResultQueryParams,
    EvaluationResultRowResponse,
    EvaluationResultOverrideRequest,
    EvaluationGenerateRequest,
    EvaluationGenerateSummaryResponse,
    EvaluationJudgeRequest,
    EvaluationJudgeSummaryResponse,
    EvaluationPayloadPreviewResponse,
    EvaluationPreviewRequest,
    EvaluationPreviewResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationRunSummaryResponse,
)
from app.services.batch_evaluation_service import (
    BatchJobNotFoundError,
    BatchJobSelectionError,
    cancel_batch_job,
    create_batch_job,
    get_batch_job,
    list_batch_jobs,
)
from app.services.evaluation_result_service import (
    EvaluationResultQueryError,
    EvaluationResultRowNotFoundError,
    clear_evaluation_result_attempt,
    list_evaluation_results,
    override_evaluation_result_attempt,
)
from app.services.evaluation_service import (
    EvalResultNotFoundError,
    EvaluationResponseTextMissingError,
    QuestionNotFoundError,
    generate_evaluation,
    judge_evaluation,
    preview_evaluation_payload,
    preview_evaluation,
    run_evaluation,
)
from app.services.model_service import ModelConfigurationError, ModelNotFoundError


router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _to_generate_summary(response: EvaluationRunResponse) -> EvaluationGenerateSummaryResponse:
    return EvaluationGenerateSummaryResponse(
        eval_result_id=response.eval_result_id,
        question_id=response.question_id,
        model_id=response.model_id,
        model_name=response.model_name,
        attempt=response.attempt,
        status="error" if response.error else "generated",
        error=response.error,
        finished_at=response.finished_at,
    )


def _to_run_summary(response: EvaluationRunResponse) -> EvaluationRunSummaryResponse:
    if response.error:
        status = "error"
    elif response.attempt_result == 1:
        status = "correct"
    elif response.attempt_result == 0:
        status = "incorrect"
    else:
        status = "unknown"

    return EvaluationRunSummaryResponse(
        eval_result_id=response.eval_result_id,
        question_id=response.question_id,
        model_id=response.model_id,
        model_name=response.model_name,
        attempt=response.attempt,
        status=status,
        error=response.error,
        finished_at=response.finished_at,
    )


def _to_judge_summary(response: EvaluationRunResponse) -> EvaluationJudgeSummaryResponse:
    return EvaluationJudgeSummaryResponse(**_to_run_summary(response).model_dump())


@router.post("/preview", response_model=EvaluationPreviewResponse)
def preview_evaluation_input(
    payload: EvaluationPreviewRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationPreviewResponse:
    try:
        return preview_evaluation(session, payload)
    except (QuestionNotFoundError, ModelNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ModelConfigurationError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/payload-preview", response_model=EvaluationPayloadPreviewResponse)
def preview_evaluation_payload_input(
    payload: EvaluationPreviewRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationPayloadPreviewResponse:
    try:
        return preview_evaluation_payload(session, payload)
    except (QuestionNotFoundError, ModelNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ModelConfigurationError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate", response_model=EvaluationGenerateSummaryResponse)
def generate_evaluation_once(
    payload: EvaluationGenerateRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationGenerateSummaryResponse:
    try:
        return _to_generate_summary(generate_evaluation(session, payload))
    except (QuestionNotFoundError, ModelNotFoundError, EvalResultNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/judge", response_model=EvaluationJudgeSummaryResponse)
def judge_evaluation_once(
    payload: EvaluationJudgeRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationJudgeSummaryResponse:
    try:
        return _to_judge_summary(judge_evaluation(session, payload))
    except (QuestionNotFoundError, ModelNotFoundError, EvalResultNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ModelConfigurationError, EvaluationResponseTextMissingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/run", response_model=EvaluationRunSummaryResponse)
def run_evaluation_once(
    payload: EvaluationRunRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationRunSummaryResponse:
    try:
        return _to_run_summary(run_evaluation(session, payload))
    except (QuestionNotFoundError, ModelNotFoundError, EvalResultNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/batch-jobs", response_model=list[EvaluationBatchJobSummaryResponse])
def list_evaluation_batch_jobs() -> list[EvaluationBatchJobSummaryResponse]:
    return list_batch_jobs()


@router.post("/batch-jobs", response_model=EvaluationBatchJobResponse, status_code=202)
def create_evaluation_batch_job(
    payload: EvaluationBatchJobCreateRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationBatchJobResponse:
    try:
        return create_batch_job(session, payload)
    except (BatchJobSelectionError, ModelConfigurationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/batch-jobs/{job_id}", response_model=EvaluationBatchJobResponse)
def get_evaluation_batch_job(job_id: str) -> EvaluationBatchJobResponse:
    try:
        return get_batch_job(job_id)
    except BatchJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/batch-jobs/{job_id}/cancel", response_model=EvaluationBatchJobResponse)
def cancel_evaluation_batch_job(job_id: str) -> EvaluationBatchJobResponse:
    try:
        return cancel_batch_job(job_id)
    except BatchJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/results", response_model=EvaluationResultListResponse)
def list_evaluation_result_rows(
    params: EvaluationResultQueryParams = Depends(),
    session: Session = Depends(db_session_dependency),
) -> EvaluationResultListResponse:
    try:
        return list_evaluation_results(session, params)
    except EvaluationResultQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/results/{eval_result_id}/clear", response_model=EvaluationResultRowResponse)
def clear_evaluation_result_attempt_data(
    eval_result_id: int,
    payload: EvaluationResultClearRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationResultRowResponse:
    try:
        return clear_evaluation_result_attempt(session, eval_result_id, payload)
    except EvaluationResultRowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/results/{eval_result_id}/override", response_model=EvaluationResultRowResponse)
def override_evaluation_result_attempt_data(
    eval_result_id: int,
    payload: EvaluationResultOverrideRequest,
    session: Session = Depends(db_session_dependency),
) -> EvaluationResultRowResponse:
    try:
        return override_evaluation_result_attempt(session, eval_result_id, payload)
    except EvaluationResultRowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
