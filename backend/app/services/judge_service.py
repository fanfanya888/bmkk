from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.clients import invoke_openai_compatible_model
from app.core.api_styles import normalize_api_style
from app.core.config import settings
from app.services.model_service import ResolvedEvalModelConfig


JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
JUDGE_SYSTEM_PROMPT = (
    "你是严格的答案校验员。"
    "你只能根据提供的模型回复、标准答案文本、标准答案图片判断是否正确。"
    "如果模型回复与标准答案一致，result 必须输出 1。"
    "如果模型回复与标准答案不一致，result 必须输出 0。"
    "不要使用题目文本，不要补充额外背景。"
    "只输出 JSON，不要输出其他内容。"
)


class JudgeConfigurationError(ValueError):
    """Raised when judge-model configuration is incomplete."""


class JudgeResponseFormatError(ValueError):
    """Raised when the judge model does not return the expected JSON payload."""


@dataclass(slots=True)
class JudgeDecision:
    result: int
    feedback: str
    raw_response_text: str


def get_judge_runtime_config() -> ResolvedEvalModelConfig:
    api_url = (settings.judge_api_url or "").strip()
    api_model = (settings.judge_api_model or "").strip()
    api_key = (settings.judge_api_key or "").strip()
    if not (api_url and api_model and api_key):
        raise JudgeConfigurationError(
            "Judge model configuration is incomplete. Set JUDGE_API_URL, JUDGE_API_MODEL and JUDGE_API_KEY."
        )

    return ResolvedEvalModelConfig(
        model_id=0,
        model_name="JudgeModel",
        api_url=api_url,
        api_style=normalize_api_style(settings.judge_api_style),
        api_model=api_model,
        api_key=api_key,
        is_active=True,
        sort_order=0,
    )


def _encode_image_as_data_url(path: Path) -> str:
    import base64
    import mimetypes

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_judge_messages(
    *,
    model_response_text: str,
    standard_answer_text: str,
    answer_image_paths: list[Path],
) -> list[dict[str, Any]]:
    answer_text = standard_answer_text.strip() or "<EMPTY>"
    response_text = model_response_text.strip() or "<EMPTY>"
    instructions = (
        "请判断“模型回复”与“标准答案”是否一致。\n"
        "输出 JSON，格式固定为："
        '{"result": 1, "feedback": "简要说明为什么对或为什么错"}'
        "\n其中 result 只能是 1 或 0。"
        "如果一致或正确，result=1；如果不一致或错误，result=0。\n\n"
        f"模型回复：\n{response_text}\n\n"
        f"标准答案文本：\n{answer_text}\n"
    )

    user_content: list[dict[str, Any]] = [{"type": "text", "text": instructions}]
    for image_path in answer_image_paths:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": _encode_image_as_data_url(image_path)},
            }
        )

    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _parse_judge_result(value: Any) -> int:
    if value in (1, "1", True, "true", "correct", "Correct", "CORRECT"):
        return 1
    if value in (0, "0", False, "false", "incorrect", "Incorrect", "INCORRECT"):
        return 0
    raise JudgeResponseFormatError(f"Judge result is invalid: {value!r}")


def parse_judge_response(raw_response_text: str) -> JudgeDecision:
    text = raw_response_text.strip()
    if not text:
        raise JudgeResponseFormatError("Judge model returned empty text.")

    payload: dict[str, Any] | None = None
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            payload = loaded
    except json.JSONDecodeError:
        payload = None

    if payload is None:
        match = JSON_OBJECT_PATTERN.search(text)
        if match:
            try:
                loaded = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise JudgeResponseFormatError("Judge model returned malformed JSON.") from exc
            if isinstance(loaded, dict):
                payload = loaded

    if payload is None:
        raise JudgeResponseFormatError("Judge model did not return a JSON object.")

    result = _parse_judge_result(payload.get("result"))
    feedback = str(
        payload.get("feedback")
        or payload.get("reason")
        or payload.get("comment")
        or payload.get("message")
        or ""
    ).strip()
    if not feedback:
        feedback = raw_response_text.strip()

    return JudgeDecision(
        result=result,
        feedback=feedback,
        raw_response_text=raw_response_text,
    )


def judge_model_response(
    *,
    model_response_text: str,
    standard_answer_text: str,
    answer_image_paths: list[Path],
) -> JudgeDecision:
    judge_config = get_judge_runtime_config()
    messages = build_judge_messages(
        model_response_text=model_response_text,
        standard_answer_text=standard_answer_text,
        answer_image_paths=answer_image_paths,
    )
    raw_response_text = invoke_openai_compatible_model(
        judge_config,
        messages,
        timeout_seconds=settings.judge_request_timeout_seconds,
        max_retries=settings.judge_request_max_retries,
    )
    return parse_judge_response(raw_response_text)
