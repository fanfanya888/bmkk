from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import db_session_dependency
from app.schemas.model import EvalModelProbeResponse, EvalModelRead, EvalModelUpdate
from app.services.model_service import (
    ModelConfigurationError,
    ModelNotFoundError,
    get_model_detail,
    list_models,
    probe_model,
    update_model,
)


router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[EvalModelRead])
def get_models(session: Session = Depends(db_session_dependency)) -> list[EvalModelRead]:
    return list_models(session)


@router.get("/{model_id}", response_model=EvalModelRead)
def get_model(model_id: int, session: Session = Depends(db_session_dependency)) -> EvalModelRead:
    try:
        return get_model_detail(session, model_id)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{model_id}", response_model=EvalModelRead)
def patch_model(
    model_id: int,
    payload: EvalModelUpdate,
    session: Session = Depends(db_session_dependency),
) -> EvalModelRead:
    try:
        return update_model(session, model_id, payload)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{model_id}/probe", response_model=EvalModelProbeResponse)
def probe_model_route(
    model_id: int,
    session: Session = Depends(db_session_dependency),
) -> EvalModelProbeResponse:
    try:
        return probe_model(session, model_id)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
