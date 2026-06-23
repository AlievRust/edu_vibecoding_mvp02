from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.config import Settings
from app.db import fetch_recent_tickets
from app.main import create_app


def make_settings(tmp_path, **overrides) -> Settings:
    base_kwargs = {
        "database_path": tmp_path / "triage.db",
        "llm_provider": "mock",
        "rate_limit_per_minute": 60,
        "yandex_cloud_folder": "folder",
        "yandex_cloud_api_key": "api-key",
        "yandex_cloud_model": "aliceai-llm/latest",
        "temperature": 0.2,
    }
    base_kwargs.update(overrides)
    return Settings(**base_kwargs)


def read_ticket_count(db_path) -> int:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()
    assert row is not None
    return int(row[0])


def test_successful_triage_saves_audit(tmp_path) -> None:
    settings = make_settings(tmp_path, llm_provider="mock")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/triage",
            json={
                "client_id": "client-1",
                "channel": "email",
                "text": "Need billing help with my invoice",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "billing"
    assert body["confidence"] == "high"
    assert body["error"] is None
    assert read_ticket_count(settings.database_path) == 1

    tickets = fetch_recent_tickets(settings.database_path)
    assert tickets[0]["category"] == "billing"
    assert tickets[0]["error"] is None


def test_empty_text_is_rejected(tmp_path) -> None:
    settings = make_settings(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/triage",
            json={
                "client_id": "client-1",
                "channel": "email",
                "text": "",
            },
        )

    assert response.status_code == 422
    assert read_ticket_count(settings.database_path) == 1
    tickets = fetch_recent_tickets(settings.database_path)
    assert tickets[0]["error"] == "validation_error"


def test_too_long_text_is_rejected(tmp_path) -> None:
    settings = make_settings(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/triage",
            json={
                "client_id": "client-1",
                "channel": "email",
                "text": "a" * 4001,
            },
        )

    assert response.status_code == 422
    assert read_ticket_count(settings.database_path) == 1
    tickets = fetch_recent_tickets(settings.database_path)
    assert tickets[0]["error"] == "validation_error"


def test_broken_provider_returns_fallback(tmp_path) -> None:
    settings = make_settings(tmp_path, llm_provider="broken")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/triage",
            json={
                "client_id": "client-1",
                "channel": "chat",
                "text": "Any problem at all",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "other"
    assert body["confidence"] == "low"
    assert body["escalate"] is True
    assert body["error"] == "provider_error"

    tickets = fetch_recent_tickets(settings.database_path)
    assert tickets[0]["error"] == "provider_error"


def test_rate_limit_returns_429(tmp_path) -> None:
    settings = make_settings(tmp_path, rate_limit_per_minute=1)
    app = create_app(settings)

    with TestClient(app) as client:
        first_response = client.post(
            "/triage",
            json={
                "client_id": "client-1",
                "channel": "chat",
                "text": "Need support",
            },
        )
        second_response = client.post(
            "/triage",
            json={
                "client_id": "client-1",
                "channel": "chat",
                "text": "Need support again",
            },
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert read_ticket_count(settings.database_path) == 2
    tickets = fetch_recent_tickets(settings.database_path)
    assert tickets[0]["error"] == "rate_limit_exceeded"

