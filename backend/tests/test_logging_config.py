from __future__ import annotations

import logging
import os

from app.core.logging import configure_process_stdio_encoding
from app.core.logging import configure_uvicorn_access_log
from app.main import create_app
from app.main import settings


class _FakeStream:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def reconfigure(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


def test_configure_process_stdio_encoding_sets_utf8(monkeypatch) -> None:
    fake_stdout = _FakeStream()
    fake_stderr = _FakeStream()

    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    monkeypatch.setattr("app.core.logging.sys.stdout", fake_stdout)
    monkeypatch.setattr("app.core.logging.sys.stderr", fake_stderr)

    configure_process_stdio_encoding()

    assert os.environ["PYTHONIOENCODING"] == "utf-8"
    assert fake_stdout.calls == [{"encoding": "utf-8"}]
    assert fake_stderr.calls == [{"encoding": "utf-8"}]


def test_configure_uvicorn_access_log_disables_logger() -> None:
    access_logger = logging.getLogger("uvicorn.access")
    original_disabled = access_logger.disabled
    original_propagate = access_logger.propagate

    try:
        access_logger.disabled = False
        access_logger.propagate = True

        configure_uvicorn_access_log(enabled=False)

        assert access_logger.disabled is True
        assert access_logger.propagate is False

        configure_uvicorn_access_log(enabled=True)

        assert access_logger.disabled is False
    finally:
        access_logger.disabled = original_disabled
        access_logger.propagate = original_propagate


def test_create_app_configures_uvicorn_access_log(monkeypatch) -> None:
    captured: dict[str, bool] = {}
    flags: dict[str, bool] = {}

    monkeypatch.setattr(settings, "backend_access_log", False)
    monkeypatch.setattr(settings, "backend_api_request_log", False)
    monkeypatch.setattr(
        "app.main.configure_process_stdio_encoding",
        lambda: flags.setdefault("stdio", True),
    )
    monkeypatch.setattr(
        "app.main.configure_uvicorn_access_log",
        lambda *, enabled: captured.setdefault("enabled", enabled),
    )

    create_app()

    assert flags == {"stdio": True}
    assert captured == {"enabled": False}
