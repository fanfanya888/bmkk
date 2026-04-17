from __future__ import annotations

from typing import Literal, TypeAlias, cast


API_STYLE_CHAT_COMPLETIONS = "chat_completions"
API_STYLE_RESPONSES = "responses"

APIStyle: TypeAlias = Literal["chat_completions", "responses"]

SUPPORTED_API_STYLES = frozenset(
    {
        API_STYLE_CHAT_COMPLETIONS,
        API_STYLE_RESPONSES,
    }
)

API_STYLE_ALIASES = {
    "chat": API_STYLE_CHAT_COMPLETIONS,
    "chat_completion": API_STYLE_CHAT_COMPLETIONS,
    "chat_completions": API_STYLE_CHAT_COMPLETIONS,
    "response": API_STYLE_RESPONSES,
    "responses": API_STYLE_RESPONSES,
}


def normalize_api_style(value: str | None) -> APIStyle:
    normalized = (value or API_STYLE_CHAT_COMPLETIONS).strip().lower()
    normalized = API_STYLE_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_API_STYLES:
        allowed = ", ".join(sorted(SUPPORTED_API_STYLES))
        raise ValueError(f"Unsupported api_style: {value!r}. Expected one of: {allowed}.")
    return cast(APIStyle, normalized)
