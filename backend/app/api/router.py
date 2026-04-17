from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import evaluations
from app.api.routes import health
from app.api.routes import models
from app.api.routes import overview


api_router = APIRouter()
api_router.include_router(evaluations.router)
api_router.include_router(health.router)
api_router.include_router(models.router)
api_router.include_router(overview.router)
