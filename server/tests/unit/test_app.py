from __future__ import annotations

from fastapi.testclient import TestClient

import device_watch_server.app as app_module
from device_watch_server.core.config import Environment, Settings

VALID_DATABASE_URL = "mysql+pymysql://device_watch:secret@db:3306/device_watch"
PRODUCTION_DATABASE_URL = (
    "mysql+pymysql://device_watch:secret@db:3306/device_watch"
    "?ssl_ca=%2Frun%2Fsecrets%2Fmysql-ca.pem"
    "&ssl_verify_cert=true&ssl_verify_identity=true"
)


def make_settings(environment: str = "test") -> Settings:
    database_url = PRODUCTION_DATABASE_URL if environment == "production" else VALID_DATABASE_URL
    return Settings(
        device_watch_env=environment,
        database_url=database_url,
    )


def test_liveness_returns_process_status_without_calling_database() -> None:
    calls = 0

    def fake_database_check() -> None:
        nonlocal calls
        calls += 1

    app = app_module.create_app(make_settings(), database_check=fake_database_check)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert calls == 0


def test_readiness_returns_200_when_database_check_succeeds() -> None:
    calls: list[str] = []

    def fake_database_check() -> None:
        calls.append("checked")

    app = app_module.create_app(make_settings(), database_check=fake_database_check)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert calls == ["checked"]


def test_readiness_returns_generic_503_when_database_check_fails() -> None:
    def fake_database_check() -> None:
        raise RuntimeError("database connection secret://user:pass@db/device_watch")

    app = app_module.create_app(make_settings(), database_check=fake_database_check)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "RuntimeError" not in response.text
    assert "secret" not in response.text.lower()
    assert "mysql" not in response.text.lower()


def test_only_stage_one_health_routes_are_registered() -> None:
    app = app_module.create_app(make_settings())

    paths = {route.path for route in app.routes if hasattr(route, "path")}

    assert paths == {"/api/v1/health/live", "/api/v1/health/ready"}


def test_production_disables_openapi_routes() -> None:
    app = app_module.create_app(make_settings(environment=Environment.PRODUCTION.value))

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_lifespan_disposes_owned_engine(monkeypatch) -> None:
    disposed: dict[str, bool] = {}

    class FakeEngine:
        def dispose(self) -> None:
            disposed["disposed"] = True

    fake_engine = FakeEngine()
    monkeypatch.setattr(app_module, "create_database_engine", lambda settings: fake_engine)

    app = app_module.create_app(make_settings())

    with TestClient(app):
        pass

    assert disposed == {"disposed": True}
