from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from app.clients.openai_compatible import ModelInvocationError
from app.services.evaluation_service import (
    _judge_response_text,
    build_multimodal_messages,
    build_question_prompt_text,
)


def test_build_question_prompt_text_uses_question_text() -> None:
    question = SimpleNamespace(content_text="如图，求阴影部分面积。")
    prompt = build_question_prompt_text(question)
    assert prompt == "如图，求阴影部分面积。"


def test_build_multimodal_messages_only_uses_content_images() -> None:
    image_path = Path(__file__).with_name("sample_test_image.png")
    image_path.write_bytes(b"fake-image")

    try:
        question = SimpleNamespace(
            content_text="如图，求面积。",
            content_images=[str(image_path)],
            answer_images=["should-not-be-used.png"],
            analysis_images=["should-not-be-used.png"],
        )

        messages = build_multimodal_messages(question)

        assert messages[0]["role"] == "user"
        user_content = messages[0]["content"]
        assert len(user_content) == 2
        assert user_content[0]["type"] == "text"
        assert user_content[0]["text"] == "如图，求面积。"
        assert user_content[1]["type"] == "image_url"
    finally:
        with suppress(FileNotFoundError):
            image_path.unlink()


def test_judge_response_text_converts_provider_error_to_attempt_error(monkeypatch) -> None:
    question = SimpleNamespace(answer_text="标准答案", answer_images=[])

    monkeypatch.setattr("app.services.evaluation_service.resolve_answer_image_paths", lambda _question: [])
    monkeypatch.setattr(
        "app.services.evaluation_service.judge_model_response",
        lambda **_: (_ for _ in ()).throw(
            ModelInvocationError("provider response is not valid JSON: <empty response body>")
        ),
    )

    attempt_result, judge_feedback, error = _judge_response_text(
        question=question,
        response_text="模型回答",
    )

    assert attempt_result is None
    assert judge_feedback is None
    assert error == "provider response is not valid JSON: <empty response body>"
