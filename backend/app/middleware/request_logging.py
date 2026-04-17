from __future__ import annotations

import logging
from time import perf_counter

from fastapi import FastAPI, Request


logger = logging.getLogger("uvicorn.error")


def _should_log_request(method: str, path: str) -> bool:
    if method == "POST" and path in {
        "/api/v1/evaluations/generate",
        "/api/v1/evaluations/judge",
        "/api/v1/evaluations/run",
        "/api/v1/evaluations/batch-jobs",
    }:
        return True

    if method == "POST" and path.startswith("/api/v1/evaluations/batch-jobs/") and path.endswith(
        "/cancel"
    ):
        return True

    if method == "PATCH" and path.startswith("/api/v1/models/"):
        return True

    if method == "POST" and path.startswith("/api/v1/models/") and path.endswith("/probe"):
        return True

    return False


def install_request_logging_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        method = request.method.upper()
        path = request.url.path

        if not _should_log_request(method, path):
            return await call_next(request)

        started_at = perf_counter()
        logger.info("收到请求 method=%s path=%s", method, path)

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_seconds = perf_counter() - started_at
            logger.exception(
                "请求异常 method=%s path=%s 用时=%.2fs error=%s",
                method,
                path,
                elapsed_seconds,
                exc,
            )
            raise

        elapsed_seconds = perf_counter() - started_at
        logger.info(
            "请求完成 method=%s path=%s status_code=%s 用时=%.2fs",
            method,
            path,
            response.status_code,
            elapsed_seconds,
        )
        return response
