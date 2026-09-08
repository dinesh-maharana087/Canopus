from __future__ import annotations

import json
from typing import Self

from fastapi import FastAPI
from fastapi.testclient import TestClient

from device_watch_server.cli import main
from device_watch_server.core.logging import sanitize_for_logging, setup_logging


def test_sanitize_for_logging_redacts_sensitive_fields() -> None:
    payload = {
        "authorization": "Bearer abc123",
        "cookie": "session=secret",
        "url": "mysql+pymysql://user:pass@db:3306/device_watch?ssl_ca=/tmp/ca.pem",
        "body": {"password": "super-secret", "ok": True},
        "nested": [{"token": "value"}],
    }

    sanitized = sanitize_for_logging(payload)
    serialized = json.dumps(sanitized)

    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["cookie"] == "[REDACTED]"
    assert sanitized["url"] == "mysql+pymysql://REDACTED@db:3306/device_watch?ssl_ca=[REDACTED]"
    assert sanitized["body"]["password"] == "[REDACTED]"
    assert "abc123" not in serialized.lower()
    assert "super-secret" not in serialized.lower()
    assert "session" not in serialized.lower()


def test_setup_logging_emits_one_line_json(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    setup_logging()

    import logging

    logger = logging.getLogger("device_watch_server")
    logger.info("request complete", extra={"event": "http_request", "method": "GET", "path": "/api/v1/health/live", "status": 200, "duration_ms": 12})

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip().splitlines()[-1])

    assert payload["level"] == "INFO"
    assert payload["event"] == "http_request"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/health/live"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 12
    assert len(captured.out.strip().splitlines()) == 1


def test_cli_success_and_failure_return_expected_exit_codes(monkeypatch, capsys) -> None:
    def fake_engine() -> object:
        class FakeConn:
            def __enter__(self) -> Self:
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def execute(self, *args, **kwargs) -> object:
                return object()

        class FakeEngine:
            def connect(self) -> FakeConn:
                return FakeConn()

            def dispose(self) -> None:
                return None

        return FakeEngine()

    monkeypatch.setattr("device_watch_server.cli.load_settings", lambda: object())
    monkeypatch.setattr("device_watch_server.cli.create_database_engine", lambda settings: fake_engine())
    monkeypatch.setattr("device_watch_server.cli.check_database", lambda engine: None)
    assert main([]) == 0
    assert "database is ready" in capsys.readouterr().out.lower()

    def boom(_: object) -> None:
        raise RuntimeError("database password=super-secret")

    monkeypatch.setattr("device_watch_server.cli.check_database", boom)
    assert main([]) == 1
    captured = capsys.readouterr()
    assert "database check failed" in captured.err.lower()
    assert "super-secret" not in captured.err.lower()


def test_logging_middleware_records_sanitized_request_summary() -> None:
    from device_watch_server.core.middleware import RequestLoggingMiddleware

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/api/test")
    def route() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.get("/api/test?token=abc123")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
