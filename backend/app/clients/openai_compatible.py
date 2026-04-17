from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from app.core.api_styles import API_STYLE_RESPONSES

if TYPE_CHECKING:
    from app.services.model_service import ResolvedEvalModelConfig


class ModelInvocationError(RuntimeError):
    """Raised when a model provider request fails or returns an unexpected payload."""


@dataclass(slots=True)
class PreparedModelRequest:
    url: str
    payload: dict[str, Any]


def _build_response_preview(response: httpx.Response) -> str:
    text = response.text.strip()
    if not text:
        return "<empty response body>"
    compact = " ".join(text.split())
    return compact[:300]


def _parse_sse_events(raw_text: str) -> list[tuple[str | None, str]]:
    events: list[tuple[str | None, str]] = []
    event_name: str | None = None
    data_lines: list[str] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            if data_lines:
                events.append((event_name, "\n".join(data_lines)))
            event_name = None
            data_lines = []
            continue

        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.removeprefix("event:").strip() or None
            continue
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())

    if data_lines:
        events.append((event_name, "\n".join(data_lines)))

    return events


def _load_sse_json_events(raw_text: str) -> list[tuple[str | None, dict[str, Any]]]:
    loaded_events: list[tuple[str | None, dict[str, Any]]] = []
    for event_name, data_text in _parse_sse_events(raw_text):
        if not data_text or data_text == "[DONE]":
            continue
        try:
            payload = httpx.Response(200, text=data_text).json()
        except ValueError as exc:
            raise ModelInvocationError("provider event stream contains invalid JSON") from exc
        if isinstance(payload, dict):
            loaded_events.append((event_name, payload))
    return loaded_events


def _extract_responses_message_text_from_sse(raw_text: str) -> str:
    events = _load_sse_json_events(raw_text)
    output_done_parts: list[str] = []
    output_delta_parts: list[str] = []

    for event_name, payload in events:
        event_type = str(payload.get("type") or event_name or "").strip()
        response_payload = payload.get("response")

        if event_type == "response.completed" and isinstance(response_payload, dict):
            return _extract_responses_message_text(response_payload)

        if isinstance(response_payload, dict) and response_payload.get("status") == "completed":
            return _extract_responses_message_text(response_payload)

        if event_type == "response.output_text.done":
            text = payload.get("text")
            if isinstance(text, str) and text.strip():
                output_done_parts.append(text)
            continue

        if event_type == "response.output_text.delta":
            delta = payload.get("delta")
            if isinstance(delta, str) and delta:
                output_delta_parts.append(delta)

    merged_done = "".join(output_done_parts).strip()
    if merged_done:
        return merged_done

    merged_delta = "".join(output_delta_parts).strip()
    if merged_delta:
        return merged_delta

    raise ModelInvocationError("provider response event stream does not contain output text")


def _extract_model_text(*, response: httpx.Response, api_style: str) -> str:
    raw_text = response.text
    content_type = response.headers.get("content-type", "").lower()
    is_event_stream = "text/event-stream" in content_type or raw_text.lstrip().startswith("event:")

    if is_event_stream:
        if api_style == API_STYLE_RESPONSES:
            return _extract_responses_message_text_from_sse(raw_text)
        raise ModelInvocationError("provider returned an unsupported event stream response")

    try:
        data = response.json()
    except ValueError as exc:
        preview = _build_response_preview(response)
        raise ModelInvocationError(f"provider response is not valid JSON: {preview}") from exc

    if not isinstance(data, dict):
        raise ModelInvocationError("provider response is not a JSON object")

    if api_style == API_STYLE_RESPONSES:
        return _extract_responses_message_text(data)

    return _extract_chat_message_text(data)


def _should_retry_status(status_code: int) -> bool:
    return status_code == 408 or status_code == 429 or 500 <= status_code < 600


def _build_chat_completions_url(api_url: str) -> str:
    normalized = api_url.strip().rstrip("/")
    if not normalized:
        raise ModelInvocationError("api_url is empty")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _build_responses_url(api_url: str) -> str:
    normalized = api_url.strip().rstrip("/")
    if not normalized:
        raise ModelInvocationError("api_url is empty")
    if normalized.endswith("/responses"):
        return normalized
    return f"{normalized}/responses"


def _extract_chat_message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ModelInvocationError("provider response does not contain choices")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ModelInvocationError("provider response does not contain a message object")

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")))
        merged = "\n".join(part for part in text_parts if part).strip()
        if merged:
            return merged

    raise ModelInvocationError("provider response message content is not supported")


def _extract_responses_message_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = payload.get("output")
    if not isinstance(output, list) or not output:
        raise ModelInvocationError("provider response does not contain output")

    text_parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")
        if item_type in {"output_text", "text"}:
            text = item.get("text")
            if text:
                text_parts.append(str(text))
            continue

        if item_type != "message":
            continue

        content = item.get("content")
        if not isinstance(content, list):
            continue

        for content_item in content:
            if isinstance(content_item, dict) and content_item.get("type") in {
                "output_text",
                "text",
            }:
                text_parts.append(str(content_item.get("text", "")))

    merged = "\n".join(part for part in text_parts if part).strip()
    if merged:
        return merged

    raise ModelInvocationError("provider response output content is not supported")


def _extract_system_instruction(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "input_text"}:
                text_parts.append(str(item.get("text", "")))
        return "\n".join(part for part in text_parts if part).strip()

    raise ModelInvocationError("system message content is not supported for responses")


def _to_responses_content_items(content: Any) -> list[dict[str, str]]:
    if isinstance(content, str):
        return [{"type": "input_text", "text": content}]

    if not isinstance(content, list):
        raise ModelInvocationError("message content is not supported for responses")

    converted: list[dict[str, str]] = []
    for item in content:
        if not isinstance(item, dict):
            raise ModelInvocationError("message content item is not supported for responses")

        item_type = item.get("type")
        if item_type in {"text", "input_text"}:
            converted.append(
                {
                    "type": "input_text",
                    "text": str(item.get("text", "")),
                }
            )
            continue

        if item_type in {"image_url", "input_image"}:
            raw_image_url = item.get("image_url")
            if isinstance(raw_image_url, dict):
                raw_image_url = raw_image_url.get("url", "")
            image_url = str(raw_image_url or "").strip()
            if not image_url:
                raise ModelInvocationError("message image content is missing image_url")
            converted.append(
                {
                    "type": "input_image",
                    "image_url": image_url,
                }
            )
            continue

        raise ModelInvocationError(f"message content type is not supported: {item_type!r}")

    return converted


def _build_responses_payload(
    model_config: ResolvedEvalModelConfig,
    messages: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    instructions_parts: list[str] = []
    input_items: list[dict[str, Any]] = []

    for message in messages:
        role = str(message.get("role", "")).strip()
        if not role:
            raise ModelInvocationError("message role is empty")

        if role == "system":
            instruction = _extract_system_instruction(message.get("content"))
            if not instruction:
                raise ModelInvocationError("system message content is empty")
            instructions_parts.append(instruction)
            continue

        input_items.append(
            {
                "role": role,
                "content": _to_responses_content_items(message.get("content")),
            }
        )

    payload: dict[str, Any] = {
        "model": model_config.api_model,
        "input": input_items,
    }
    if instructions_parts:
        payload["instructions"] = "\n\n".join(instructions_parts)
    return payload


def build_openai_compatible_request(
    model_config: ResolvedEvalModelConfig,
    messages: Sequence[dict[str, Any]],
) -> PreparedModelRequest:
    if model_config.api_style == API_STYLE_RESPONSES:
        return PreparedModelRequest(
            url=_build_responses_url(model_config.api_url),
            payload=_build_responses_payload(model_config, messages),
        )

    return PreparedModelRequest(
        url=_build_chat_completions_url(model_config.api_url),
        payload={
            "model": model_config.api_model,
            "messages": list(messages),
        },
    )


def invoke_openai_compatible_model(
    model_config: ResolvedEvalModelConfig,
    messages: Sequence[dict[str, Any]],
    *,
    timeout_seconds: float,
    max_retries: int = 0,
) -> str:
    request = build_openai_compatible_request(model_config, messages)
    headers = {
        "Authorization": f"Bearer {model_config.api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
                response = client.post(request.url, headers=headers, json=request.payload)
            response.raise_for_status()
            return _extract_model_text(response=response, api_style=model_config.api_style)
        except httpx.HTTPStatusError as exc:
            if attempt < max_retries and _should_retry_status(exc.response.status_code):
                continue
            detail = _build_response_preview(exc.response)
            raise ModelInvocationError(
                f"provider returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.TransportError as exc:
            if attempt < max_retries:
                continue
            raise ModelInvocationError(f"provider request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ModelInvocationError(f"provider request failed: {exc}") from exc

    raise ModelInvocationError("provider request failed after retries")
