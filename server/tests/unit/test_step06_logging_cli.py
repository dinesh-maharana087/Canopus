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


def test_setup_logging_emits_newline_delimited_json_records(
    monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    setup_logging()

    import logging

    logger = logging.getLogger("device_watch_server")
    logger.info("first record", extra={"event": "first"})
    logger.info("second record", extra={"event": "second"})

    captured = capsys.readouterr()
    assert captured.out.count("\n") == 2

    payloads = [json.loads(line) for line in captured.out.splitlines()]
    assert [payload["event"] for payload in payloads] == ["first", "second"]
    assert all(payload["level"] == "INFO" for payload in payloads)


def test_cli_success_prints_only_the_approved_status(monkeypatch, capsys) -> None:
    disposed: list[bool] = []

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
            disposed.append(True)

    monkeypatch.setattr("device_watch_server.cli.load_settings", lambda: object())
    monkeypatch.setattr(
        "device_watch_server.cli.create_database_engine", lambda settings: FakeEngine()
    )

    assert main([]) == 0

    captured = capsys.readouterr()
    assert captured.out == "database connectivity: ok\n"
    assert captured.err == ""
    assert disposed == [True]


def test_cli_failure_prints_only_the_approved_sanitized_status(
    monkeypatch, capsys
) -> None:
    disposed: list[bool] = []

    class FailingEngine:
        def connect(self) -> object:
            raise OSError(
                "database secret://private-user:private-pass@db/device_watch"
            )

        def dispose(self) -> None:
            disposed.append(True)

    monkeypatch.setattr("device_watch_server.cli.load_settings", lambda: object())
    monkeypatch.setattr(
        "device_watch_server.cli.create_database_engine", lambda settings: FailingEngine()
    )
    assert main([]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "database connectivity: unavailable\n"
    assert "private-user" not in captured.out + captured.err
    assert "private-pass" not in captured.out + captured.err
    assert disposed == [True]


def test_logging_middleware_records_only_the_approved_request_fields(capsys) -> None:
    from device_watch_server.core.middleware import RequestLoggingMiddleware

    setup_logging()
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/api/devices/{device_id}")
    def route(device_id: str) -> dict[str, str]:
        del device_id
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.get("/api/devices/private-device?token=abc123")

    captured = capsys.readouterr()
    payloads = [json.loads(line) for line in captured.out.splitlines()]

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(payloads) == 1
    assert set(payloads[0]) == {
        "duration_ms",
        "event",
        "level",
        "logger",
        "message",
        "method",
        "normalized_path",
        "status",
        "timestamp",
    }
    assert payloads[0]["event"] == "http_request"
    assert payloads[0]["method"] == "GET"
    assert payloads[0]["normalized_path"] == "/api/devices/{device_id}"
    assert payloads[0]["status"] == 200
    assert "abc123" not in captured.out
    assert "private-device" not in captured.out


def test_logging_middleware_does_not_log_an_unmatched_raw_path(capsys) -> None:
    from device_watch_server.core.middleware import RequestLoggingMiddleware

    setup_logging()
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    with TestClient(app) as client:
        response = client.get("/private-unmatched-secret")

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert response.status_code == 404
    assert payload["normalized_path"] == "<unmatched>"
    assert "private-unmatched-secret" not in captured.out
