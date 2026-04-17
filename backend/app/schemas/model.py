from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core.api_styles import APIStyle


class EvalModelRead(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    model_name: str
    release_date: date | None = None
    api_url: str
    api_style: APIStyle
    api_model: str
    has_api_key: bool
    is_configured: bool
    is_active: bool
    sort_order: int


class EvalModelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_name: str | None = Field(default=None, min_length=1)
    release_date: date | None = None
    api_url: str | None = None
    api_style: APIStyle | None = None
    api_model: str | None = None
    api_key: SecretStr | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class EvalModelProbeResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    model_name: str
    api_style: APIStyle
    api_model: str
    ok: bool
    latency_ms: int
    provider_error: str | None
    response_text_preview: str | None
