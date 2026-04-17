from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.db.session import db_session_dependency
from app.main import app
from app.schemas.model import EvalModelProbeResponse, EvalModelRead


client = TestClient(app)


def test_get_model_route_returns_service_payload(monkeypatch) -> None:
    def fake_get_model_detail(session, model_id: int) -> EvalModelRead:
        assert model_id == 7
        return EvalModelRead(
            model_id=7,
            model_name="DeepSeek",
            release_date=date(2024, 12, 26),
            api_url="https://example.test/v1",
            api_style="chat_completions",
            api_model="deepseek-chat",
            has_api_key=True,
            is_configured=True,
            is_active=True,
            sort_order=6,
        )

    monkeypatch.setattr("app.api.routes.models.get_model_detail", fake_get_model_detail)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.get("/api/v1/models/7")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["model_name"] == "DeepSeek"
    assert response.json()["release_date"] == "2024-12-26"
    assert response.json()["has_api_key"] is True
    assert response.json()["is_configured"] is True


def test_patch_model_route_never_returns_api_key(monkeypatch) -> None:
    def fake_update_model(session, model_id: int, payload) -> EvalModelRead:
        assert model_id == 2
        assert payload.api_url == "https://example.test/v1"
        assert payload.api_key is not None
        return EvalModelRead(
            model_id=2,
            model_name="Claude",
            release_date=payload.release_date,
            api_url=payload.api_url,
            api_style="responses",
            api_model="claude-sonnet-4-20250514",
            has_api_key=True,
            is_configured=True,
            is_active=True,
            sort_order=2,
        )

    monkeypatch.setattr("app.api.routes.models.update_model", fake_update_model)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.patch(
            "/api/v1/models/2",
            json={
                "release_date": "2025-02-24",
                "api_url": "https://example.test/v1",
                "api_model": "claude-sonnet-4-20250514",
                "api_key": "secret-value",
            },
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["has_api_key"] is True
    assert body["release_date"] == "2025-02-24"
    assert body["api_style"] == "responses"
    assert "api_key" not in body


def test_probe_model_route_returns_provider_status(monkeypatch) -> None:
    def fake_probe_model(session, model_id: int) -> EvalModelProbeResponse:
        assert model_id == 6
        return EvalModelProbeResponse(
            model_id=6,
            model_name="DeepSeek",
            api_style="chat_completions",
            api_model="deepseek-v3",
            ok=False,
            latency_ms=321,
            provider_error="provider returned HTTP 400: model not found",
            response_text_preview=None,
        )

    monkeypatch.setattr("app.api.routes.models.probe_model", fake_probe_model)
    app.dependency_overrides[db_session_dependency] = lambda: None

    try:
        response = client.post("/api/v1/models/6/probe")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is False
    assert "model not found" in body["provider_error"]
