from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients import ModelInvocationError, invoke_openai_compatible_model
from app.core.api_styles import APIStyle, normalize_api_style
from app.models import EvalModel
from app.schemas.model import EvalModelProbeResponse, EvalModelRead, EvalModelUpdate


class ModelNotFoundError(LookupError):
    """Raised when the requested model row does not exist."""


class ModelConfigurationError(ValueError):
    """Raised when the model row exists but cannot be used."""


@dataclass(slots=True)
class ResolvedEvalModelConfig:
    model_id: int
    model_name: str
    api_url: str
    api_style: APIStyle
    api_model: str
    api_key: str
    is_active: bool
    sort_order: int

    @property
    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_model and self.api_key)


def _to_model_read(row: EvalModel) -> EvalModelRead:
    has_api_key = bool(row.api_key)
    return EvalModelRead(
        model_id=row.model_id,
        model_name=row.model_name,
        release_date=row.release_date,
        api_url=row.api_url,
        api_style=normalize_api_style(row.api_style),
        api_model=row.api_model,
        has_api_key=has_api_key,
        is_configured=bool(row.api_url and row.api_model and row.api_key),
        is_active=row.is_active,
        sort_order=row.sort_order,
    )


def _get_model_row(session: Session, model_id: int) -> EvalModel:
    row = session.get(EvalModel, model_id)
    if row is None:
        raise ModelNotFoundError(f"eval model {model_id} does not exist")
    return row


def list_models(session: Session) -> list[EvalModelRead]:
    stmt = select(EvalModel).order_by(EvalModel.sort_order.asc(), EvalModel.model_id.asc())
    rows = session.scalars(stmt).all()
    return [_to_model_read(row) for row in rows]


def get_model_detail(session: Session, model_id: int) -> EvalModelRead:
    return _to_model_read(_get_model_row(session, model_id))


def update_model(session: Session, model_id: int, payload: EvalModelUpdate) -> EvalModelRead:
    row = _get_model_row(session, model_id)

    if "model_name" in payload.model_fields_set and payload.model_name is not None:
        row.model_name = payload.model_name.strip()
    if "release_date" in payload.model_fields_set:
        row.release_date = payload.release_date
    if "api_url" in payload.model_fields_set:
        row.api_url = (payload.api_url or "").strip()
    if "api_style" in payload.model_fields_set and payload.api_style is not None:
        row.api_style = payload.api_style
    if "api_model" in payload.model_fields_set:
        row.api_model = (payload.api_model or "").strip()
    if "api_key" in payload.model_fields_set:
        row.api_key = "" if payload.api_key is None else payload.api_key.get_secret_value().strip()
    if "is_active" in payload.model_fields_set and payload.is_active is not None:
        row.is_active = payload.is_active
    if "sort_order" in payload.model_fields_set and payload.sort_order is not None:
        row.sort_order = payload.sort_order

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ModelConfigurationError("model update failed because of a database constraint") from exc

    session.refresh(row)
    return _to_model_read(row)


def get_model_runtime_config(
    session: Session,
    model_id: int,
    *,
    require_active: bool = True,
    require_credentials: bool = True,
) -> ResolvedEvalModelConfig:
    row = _get_model_row(session, model_id)
    resolved = ResolvedEvalModelConfig(
        model_id=row.model_id,
        model_name=row.model_name,
        api_url=row.api_url.strip(),
        api_style=normalize_api_style(row.api_style),
        api_model=row.api_model.strip(),
        api_key=row.api_key.strip(),
        is_active=row.is_active,
        sort_order=row.sort_order,
    )

    if require_active and not resolved.is_active:
        raise ModelConfigurationError(f"eval model {model_id} is inactive")
    if require_credentials and not resolved.is_configured:
        raise ModelConfigurationError(
            f"eval model {model_id} is not fully configured with api_url, api_model and api_key"
        )

    return resolved


def probe_model(session: Session, model_id: int) -> EvalModelProbeResponse:
    resolved = get_model_runtime_config(session, model_id)
    messages = [
        {
            "role": "system",
            "content": "You are a model connectivity probe. Reply with exactly: pong",
        },
        {
            "role": "user",
            "content": "Reply with exactly: pong",
        },
    ]

    started_at = perf_counter()
    response_text: str | None = None
    provider_error: str | None = None

    try:
        response_text = invoke_openai_compatible_model(
            resolved,
            messages,
            timeout_seconds=30.0,
        )
    except ModelInvocationError as exc:
        provider_error = str(exc)

    latency_ms = int((perf_counter() - started_at) * 1000)
    return EvalModelProbeResponse(
        model_id=resolved.model_id,
        model_name=resolved.model_name,
        api_style=resolved.api_style,
        api_model=resolved.api_model,
        ok=provider_error is None,
        latency_ms=latency_ms,
        provider_error=provider_error,
        response_text_preview=None if response_text is None else response_text[:200],
    )
