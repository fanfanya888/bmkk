from __future__ import annotations

import httpx
import pytest

from app.clients.openai_compatible import (
    ModelInvocationError,
    _extract_responses_message_text_from_sse,
    _extract_responses_message_text,
    build_openai_compatible_request,
    invoke_openai_compatible_model,
)
from app.core.api_styles import normalize_api_style
from app.core.config import Settings
from app.services.model_service import ResolvedEvalModelConfig


def build_model_config(*, api_style: str) -> ResolvedEvalModelConfig:
    return ResolvedEvalModelConfig(
        model_id=1,
        model_name="TestModel",
        api_url="https://example.test/v1",
        api_style=api_style,
        api_model="test-model",
        api_key="secret",
        is_active=True,
        sort_order=0,
    )


def test_build_openai_compatible_request_for_chat_completions() -> None:
    request = build_openai_compatible_request(
        build_model_config(api_style="chat_completions"),
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "题目文本"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,abc"},
                    },
                ],
            }
        ],
    )

    assert request.url == "https://example.test/v1/chat/completions"
    assert request.payload["messages"][0]["content"][0]["type"] == "text"
    assert request.payload["messages"][0]["content"][1]["type"] == "image_url"


def test_build_openai_compatible_request_for_responses() -> None:
    request = build_openai_compatible_request(
        build_model_config(api_style="responses"),
        [
            {
                "role": "system",
                "content": "你是严格的判卷助手。",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "题目文本"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,abc"},
                    },
                ],
            },
        ],
    )

    assert request.url == "https://example.test/v1/responses"
    assert request.payload["instructions"] == "你是严格的判卷助手。"
    assert request.payload["input"][0]["content"][0]["type"] == "input_text"
    assert request.payload["input"][0]["content"][1]["type"] == "input_image"


def test_extract_responses_message_text_reads_output_message() -> None:
    text = _extract_responses_message_text(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "第一行"},
                        {"type": "output_text", "text": "第二行"},
                    ],
                }
            ]
        }
    )

    assert text == "第一行\n第二行"


def test_extract_responses_message_text_reads_sse_completed_event() -> None:
    text = _extract_responses_message_text_from_sse(
        """event: response.created
data: {"type":"response.created","response":{"status":"in_progress"}}

event: response.completed
data: {"type":"response.completed","response":{"output":[{"type":"message","content":[{"type":"output_text","text":"判分完成"}]}]}}
"""
    )

    assert text == "判分完成"


def test_extract_responses_message_text_reads_sse_delta_events() -> None:
    text = _extract_responses_message_text_from_sse(
        """event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"第一段"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"第二段"}
"""
    )

    assert text == "第一段第二段"


def test_normalize_api_style_accepts_response_alias() -> None:
    assert normalize_api_style("response") == "responses"


def test_settings_accepts_response_alias_for_judge_api_style() -> None:
    settings = Settings(
        POSTGRES_PASSWORD="postgre",
        judge_api_style="response",
    )

    assert settings.judge_api_style == "responses"

def test_invoke_openai_compatible_model_exposes_invalid_json_preview(monkeypatch) -> None:
    class FakeResponse:
        text = "<html>upstream gateway error</html>"
        headers = {"content-type": "text/html"}

        def raise_for_status(self) -> None:
            return None

        def json(self):
            raise ValueError("not json")

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, url, headers, json):
            return FakeResponse()

    monkeypatch.setattr("app.clients.openai_compatible.httpx.Client", FakeClient)

    with pytest.raises(ModelInvocationError, match="provider response is not valid JSON: <html>upstream gateway error</html>"):
        invoke_openai_compatible_model(
            build_model_config(api_style="responses"),
            [{"role": "user", "content": [{"type": "text", "text": "题目"}]}],
            timeout_seconds=30,
        )



def test_invoke_openai_compatible_model_reads_responses_sse(monkeypatch) -> None:
    class FakeResponse:
        text = """event: response.created
data: {"type":"response.created","response":{"status":"in_progress"}}

event: response.completed
data: {"type":"response.completed","response":{"output":[{"type":"message","content":[{"type":"output_text","text":"最终结果"}]}]}}
"""
        headers = {"content-type": "text/event-stream"}

        def raise_for_status(self) -> None:
            return None

        def json(self):
            raise ValueError("not json")

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, url, headers, json):
            return FakeResponse()

    monkeypatch.setattr("app.clients.openai_compatible.httpx.Client", FakeClient)

    text = invoke_openai_compatible_model(
        build_model_config(api_style="responses"),
        [{"role": "user", "content": [{"type": "text", "text": "题目"}]}],
        timeout_seconds=30,
    )

    assert text == "最终结果"


def test_invoke_openai_compatible_model_retries_transient_transport_error(monkeypatch) -> None:
    request = httpx.Request("POST", "https://example.test/v1/responses")
    responses = [
        httpx.ReadError("unexpected eof", request=request),
        {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "重试成功"}],
                }
            ]
        },
    ]

    class FakeResponse:
        headers = {"content-type": "application/json"}

        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload
            self.text = '{"ok":true}'

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, url, headers, json):
            current = responses.pop(0)
            if isinstance(current, Exception):
                raise current
            return FakeResponse(current)

    monkeypatch.setattr("app.clients.openai_compatible.httpx.Client", FakeClient)

    text = invoke_openai_compatible_model(
        build_model_config(api_style="responses"),
        [{"role": "user", "content": [{"type": "text", "text": "题目"}]}],
        timeout_seconds=30,
        max_retries=1,
    )

    assert text == "重试成功"
