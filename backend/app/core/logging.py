from __future__ import annotations

import logging
import os
import sys


def configure_process_stdio_encoding() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def configure_uvicorn_access_log(*, enabled: bool) -> None:
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.disabled = not enabled
    if not enabled:
        access_logger.propagate = False
