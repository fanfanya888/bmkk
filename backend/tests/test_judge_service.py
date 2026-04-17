from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from app.services.judge_service import (
    build_judge_messages,
    judge_model_response,
    parse_judge_response,
)


def test_parse_judge_response_accepts_json_payload() -> None:
    decision = parse_judge_response('{"result": 1, "feedback": "标准答案一致"}')
    assert decision.result == 1
    assert decision.feedback == "标准答案一致"


def test_parse_judge_response_extracts_embedded_json() -> None:
    decision = parse_judge_response('结论如下：{"result": 0, "feedback": "答案不一致"}')
    assert decision.result == 0
    assert decision.feedback == "答案不一致"


def test_build_judge_messages_uses_answer_images_only() -> None:
    image_path = Path(__file__).with_name("sample_answer_image.png")
    image_path.write_bytes(b"fake-image")

    try:
        messages = build_judge_messages(
            model_response_text="模型回答是 62 平方厘米",
            standard_answer_text="标准答案是 62 平方厘米",
            answer_image_paths=[image_path],
        )
        assert messages[0]["role"] == "system"
        assert "result 必须输出 1" in messages[0]["content"]
        assert "result 必须输出 0" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        user_content = messages[1]["content"]
        assert user_content[0]["type"] == "text"
        assert "result=1" in user_content[0]["text"]
        assert "result=0" in user_content[0]["text"]
        assert user_content[1]["type"] == "image_url"
    finally:
        with suppress(FileNotFoundError):
            image_path.unlink()


def test_judge_model_response_uses_configured_retry_count(monkeypatch) -> None:
    captured: dict[str, int] = {}

    monkeypatch.setattr("app.services.judge_service.settings.judge_api_url", "https://example.test/v1")
    monkeypatch.setattr("app.services.judge_service.settings.judge_api_model", "judge-model")
    monkeypatch.setattr("app.services.judge_service.settings.judge_api_key", "secret")
    monkeypatch.setattr("app.services.judge_service.settings.judge_api_style", "responses")
    monkeypatch.setattr("app.services.judge_service.settings.judge_request_timeout_seconds", 120.0)
    monkeypatch.setattr("app.services.judge_service.settings.judge_request_max_retries", 1)
    monkeypatch.setattr(
        "app.services.judge_service.invoke_openai_compatible_model",
        lambda model_config, messages, timeout_seconds, max_retries=0: captured.update(
            {"max_retries": max_retries}
        )
        or '{"result": 1, "feedback": "一致"}',
    )

    decision = judge_model_response(
        model_response_text="模型回复",
        standard_answer_text="标准答案",
        answer_image_paths=[],
    )

    assert captured == {"max_retries": 1}
    assert decision.result == 1
