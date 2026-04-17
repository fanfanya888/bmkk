from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import BACKEND_ROOT
from app.core.config import settings
from app.core.logging import configure_process_stdio_encoding
from app.core.logging import configure_uvicorn_access_log
from app.middleware.request_logging import install_request_logging_middleware


def create_app() -> FastAPI:
    configure_process_stdio_encoding()
    configure_uvicorn_access_log(enabled=settings.backend_access_log)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.is_development,
    )
    if settings.backend_api_request_log:
        install_request_logging_middleware(app)
    app.mount(
        f"{settings.api_v1_prefix}/assets/images",
        StaticFiles(directory=BACKEND_ROOT / "images"),
        name="evaluation-images",
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
