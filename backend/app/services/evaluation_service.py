from __future__ import annotations

import base64
import logging
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.clients import (
    ModelInvocationError,
    build_openai_compatible_request,
    invoke_openai_compatible_model,
)
from app.core.config import settings
from app.models import EvalResult, Question
from app.schemas.evaluation import (
    EvaluationGenerateRequest,
    EvaluationPayloadPreviewResponse,
    EvaluationPreviewRequest,
    EvaluationPreviewResponse,
    EvaluationJudgeRequest,
    EvaluationRunRequest,
    EvaluationRunResponse,
)
from app.services.judge_service import (
    JudgeConfigurationError,
    JudgeResponseFormatError,
    judge_model_response,
)
from app.services.model_service import (
    ModelConfigurationError,
    ModelNotFoundError,
    ResolvedEvalModelConfig,
    get_model_runtime_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger("uvicorn.error")


class QuestionNotFoundError(LookupError):
    """Raised when the requested question row does not exist."""


class EvalResultNotFoundError(LookupError):
    """Raised when the evaluation row for a question/model pair does not exist."""


class EvaluationResponseTextMissingError(ValueError):
    """Raised when judge-only execution has no stored model response to read."""


def get_question_or_raise(session: Session, question_id: int) -> Question:
    question = session.get(Question, question_id)
    if question is None:
        raise QuestionNotFoundError(f"question {question_id} does not exist")
    return question


def get_eval_result_or_raise(session: Session, question_id: int, model_id: int) -> EvalResult:
    row = (
        session.query(EvalResult)
        .filter(
            EvalResult.question_id == question_id,
            EvalResult.model_id == model_id,
        )
        .one_or_none()
    )
    if row is None:
        raise EvalResultNotFoundError(
            f"eval_results row for question {question_id} and model {model_id} does not exist"
        )
    return row


def build_question_prompt_text(question: Question) -> str:
    return question.content_text.strip()


def _resolve_image_paths(raw_paths: list[Any]) -> list[Path]:
    resolved_paths: list[Path] = []
    for raw_path in raw_paths:
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"image does not exist: {path}")
        resolved_paths.append(path)
    return resolved_paths


def resolve_content_image_paths(question: Question) -> list[Path]:
    return _resolve_image_paths(question.content_images)


def resolve_answer_image_paths(question: Question) -> list[Path]:
    return _resolve_image_paths(question.answer_images)


def _encode_image_as_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_multimodal_messages(question: Question) -> list[dict[str, Any]]:
    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": build_question_prompt_text(question),
        }
    ]
    for image_path in resolve_content_image_paths(question):
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": _encode_image_as_data_url(image_path)},
            }
        )

    return [{"role": "user", "content": user_content}]


def preview_evaluation_payload(
    session: Session,
    payload: EvaluationPreviewRequest,
) -> EvaluationPayloadPreviewResponse:
    question = get_question_or_raise(session, payload.question_id)
    model_config = get_model_runtime_config(
        session,
        payload.model_id,
        require_active=False,
        require_credentials=False,
    )

    request_preview = build_openai_compatible_request(
        model_config,
        build_multimodal_messages(question),
    )

    return EvaluationPayloadPreviewResponse(
        question_id=question.question_id,
        model_id=model_config.model_id,
        model_name=model_config.model_name,
        api_style=model_config.api_style,
        api_model=model_config.api_model,
        request_url=request_preview.url,
        payload=request_preview.payload,
    )


def preview_evaluation(session: Session, payload: EvaluationPreviewRequest) -> EvaluationPreviewResponse:
    question = get_question_or_raise(session, payload.question_id)
    model_config = get_model_runtime_config(
        session,
        payload.model_id,
        require_active=False,
        require_credentials=False,
    )
    content_image_paths = [
        str(path.relative_to(PROJECT_ROOT)) for path in resolve_content_image_paths(question)
    ]
    return EvaluationPreviewResponse(
        question_id=question.question_id,
        model_id=model_config.model_id,
        model_name=model_config.model_name,
        model_is_active=model_config.is_active,
        model_is_configured=model_config.is_configured,
        prompt_text=build_question_prompt_text(question),
        content_image_paths=content_image_paths,
    )


def _set_attempt_fields(
    row: EvalResult,
    *,
    attempt: int,
    result: int | None,
    response_text: str | None,
    judge_feedback: str | None,
    error: str | None,
    finished_at: datetime,
) -> None:
    setattr(row, f"attempt_{attempt}_result", result)
    setattr(row, f"attempt_{attempt}_response_text", response_text)
    setattr(row, f"attempt_{attempt}_judge_feedback", judge_feedback)
    setattr(row, f"attempt_{attempt}_error", error)
    setattr(row, f"attempt_{attempt}_finished_at", finished_at)


def _run_model_with_timeout(
    question: Question,
    model_config: ResolvedEvalModelConfig,
    timeout_seconds: float,
) -> str:
    messages = build_multimodal_messages(question)
    return invoke_openai_compatible_model(
        model_config,
        messages,
        timeout_seconds=timeout_seconds,
    )


def _judge_response_text(
    *,
    question: Question,
    response_text: str,
) -> tuple[int | None, str | None, str | None]:
    judge_feedback: str | None = None
    attempt_result: int | None = None
    error: str | None = None

    try:
        judge_decision = judge_model_response(
            model_response_text=response_text,
            standard_answer_text=question.answer_text,
            answer_image_paths=resolve_answer_image_paths(question),
        )
        judge_feedback = judge_decision.feedback
        attempt_result = judge_decision.result
    except (
        FileNotFoundError,
        ModelInvocationError,
        JudgeConfigurationError,
        JudgeResponseFormatError,
    ) as exc:
        error = str(exc)

    return attempt_result, judge_feedback, error


def generate_evaluation(
    session: Session,
    payload: EvaluationGenerateRequest,
) -> EvaluationRunResponse:
    question = get_question_or_raise(session, payload.question_id)
    model_config = get_model_runtime_config(session, payload.model_id)
    eval_result = get_eval_result_or_raise(session, payload.question_id, payload.model_id)

    finished_at = datetime.now(UTC)
    response_text: str | None = None
    error: str | None = None
    started_at = perf_counter()

    logger.info(
        "开始生成模型回复 question_id=%s model_id=%s attempt=%s persist_result=%s",
        payload.question_id,
        payload.model_id,
        payload.attempt,
        payload.persist_result,
    )

    try:
        timeout_seconds = payload.request_timeout_seconds or settings.model_request_timeout_seconds
        response_text = _run_model_with_timeout(question, model_config, timeout_seconds)
    except (
        FileNotFoundError,
        ModelConfigurationError,
        ModelInvocationError,
    ) as exc:
        error = str(exc)

    if payload.persist_result:
        _set_attempt_fields(
            eval_result,
            attempt=payload.attempt,
            result=None,
            response_text=response_text,
            judge_feedback=None,
            error=error,
            finished_at=finished_at,
        )
        session.commit()

    elapsed_seconds = perf_counter() - started_at
    logger.info(
        "模型回复生成结束 eval_result_id=%s question_id=%s model_id=%s attempt=%s 状态=%s 用时=%.2fs 错误=%s",
        eval_result.eval_result_id,
        payload.question_id,
        payload.model_id,
        payload.attempt,
        "失败" if error else "成功",
        elapsed_seconds,
        error,
    )

    return EvaluationRunResponse(
        eval_result_id=eval_result.eval_result_id,
        question_id=question.question_id,
        model_id=model_config.model_id,
        model_name=model_config.model_name,
        attempt=payload.attempt,
        attempt_result=None,
        response_text=response_text,
        judge_feedback=None,
        error=error,
        finished_at=finished_at,
    )


def judge_evaluation(
    session: Session,
    payload: EvaluationJudgeRequest,
) -> EvaluationRunResponse:
    question = get_question_or_raise(session, payload.question_id)
    model_config = get_model_runtime_config(
        session,
        payload.model_id,
        require_active=False,
        require_credentials=False,
    )
    eval_result = get_eval_result_or_raise(session, payload.question_id, payload.model_id)

    finished_at = datetime.now(UTC)
    response_text = getattr(eval_result, f"attempt_{payload.attempt}_response_text")
    if not response_text:
        logger.warning(
            "仅判分失败：缺少模型回复 question_id=%s model_id=%s attempt=%s",
            payload.question_id,
            payload.model_id,
            payload.attempt,
        )
        raise EvaluationResponseTextMissingError(
            f"attempt_{payload.attempt}_response_text is empty for question {payload.question_id} and model {payload.model_id}"
        )

    judge_feedback: str | None = None
    attempt_result: int | None = None
    error: str | None = None
    started_at = perf_counter()

    logger.info(
        "开始判分 question_id=%s model_id=%s attempt=%s persist_result=%s",
        payload.question_id,
        payload.model_id,
        payload.attempt,
        payload.persist_result,
    )

    attempt_result, judge_feedback, error = _judge_response_text(
        question=question,
        response_text=response_text,
    )

    if payload.persist_result:
        _set_attempt_fields(
            eval_result,
            attempt=payload.attempt,
            result=attempt_result,
            response_text=response_text,
            judge_feedback=judge_feedback,
            error=error,
            finished_at=finished_at,
        )
        session.commit()

    elapsed_seconds = perf_counter() - started_at
    logger.info(
        "判分结束 eval_result_id=%s question_id=%s model_id=%s attempt=%s 状态=%s 判分结果=%s 用时=%.2fs 错误=%s",
        eval_result.eval_result_id,
        payload.question_id,
        payload.model_id,
        payload.attempt,
        "失败" if error else "成功",
        attempt_result,
        elapsed_seconds,
        error,
    )

    return EvaluationRunResponse(
        eval_result_id=eval_result.eval_result_id,
        question_id=question.question_id,
        model_id=model_config.model_id,
        model_name=model_config.model_name,
        attempt=payload.attempt,
        attempt_result=attempt_result,
        response_text=response_text,
        judge_feedback=judge_feedback,
        error=error,
        finished_at=finished_at,
    )


def run_evaluation(session: Session, payload: EvaluationRunRequest) -> EvaluationRunResponse:
    started_at = perf_counter()
    logger.info(
        "开始组合评测 question_id=%s model_id=%s attempt=%s persist_result=%s",
        payload.question_id,
        payload.model_id,
        payload.attempt,
        payload.persist_result,
    )
    generated = generate_evaluation(
        session,
        EvaluationGenerateRequest(
            question_id=payload.question_id,
            model_id=payload.model_id,
            attempt=payload.attempt,
            persist_result=False,
            request_timeout_seconds=payload.request_timeout_seconds,
        ),
    )
    if generated.error:
        if payload.persist_result:
            eval_result = get_eval_result_or_raise(session, payload.question_id, payload.model_id)
            _set_attempt_fields(
                eval_result,
                attempt=payload.attempt,
                result=None,
                response_text=generated.response_text,
                judge_feedback=None,
                error=generated.error,
                finished_at=generated.finished_at,
            )
            session.commit()
        elapsed_seconds = perf_counter() - started_at
        logger.info(
            "组合评测结束 eval_result_id=%s question_id=%s model_id=%s attempt=%s 状态=失败 用时=%.2fs 错误=%s",
            generated.eval_result_id,
            payload.question_id,
            payload.model_id,
            payload.attempt,
            elapsed_seconds,
            generated.error,
        )
        return generated

    attempt_result, judge_feedback, error = _judge_response_text(
        question=get_question_or_raise(session, payload.question_id),
        response_text=generated.response_text or "",
    )
    if payload.persist_result:
        eval_result = get_eval_result_or_raise(session, payload.question_id, payload.model_id)
        _set_attempt_fields(
            eval_result,
            attempt=payload.attempt,
            result=attempt_result,
            response_text=generated.response_text,
            judge_feedback=judge_feedback,
            error=error,
            finished_at=datetime.now(UTC),
        )
        session.commit()

    elapsed_seconds = perf_counter() - started_at
    logger.info(
        "组合评测结束 eval_result_id=%s question_id=%s model_id=%s attempt=%s 状态=%s 用时=%.2fs 错误=%s",
        generated.eval_result_id,
        payload.question_id,
        payload.model_id,
        payload.attempt,
        "失败" if error else "成功",
        elapsed_seconds,
        error,
    )

    return EvaluationRunResponse(
        eval_result_id=generated.eval_result_id,
        question_id=generated.question_id,
        model_id=generated.model_id,
        model_name=generated.model_name,
        attempt=generated.attempt,
        attempt_result=attempt_result,
        response_text=generated.response_text,
        judge_feedback=judge_feedback,
        error=error,
        finished_at=datetime.now(UTC),
    )
