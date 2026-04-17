from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_sync_session
from app.schemas.health import DatabaseHealthResponse, HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/db", response_model=DatabaseHealthResponse)
def database_health_check() -> DatabaseHealthResponse:
    try:
        with get_sync_session() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc

    return DatabaseHealthResponse(status="ok", database="reachable")
