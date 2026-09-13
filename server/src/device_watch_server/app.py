"""FastAPI application factory for the Device Watch server."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from device_watch_server.api.router import api_router
from device_watch_server.core.config import Settings, load_settings
from device_watch_server.core.logging import setup_logging
from device_watch_server.core.middleware import RequestLoggingMiddleware
from device_watch_server.db.engine import create_database_engine
from device_watch_server.db.health import check_database
from device_watch_server.enrollment.transaction import EnrollmentResult, enroll_device


def create_app(
    settings: Settings | None = None,
    database_check: Callable[[], None] | None = None,
) -> FastAPI:
    """Create a FastAPI app with an internal engine when needed."""

    resolved_settings = settings or load_settings()
    engine: Engine | None = None
    engine_lock = Lock()

    def owned_engine() -> Engine:
        nonlocal engine
        with engine_lock:
            if engine is None:
                engine = create_database_engine(resolved_settings)
            return engine

    def default_database_check() -> None:
        check_database(owned_engine())

    def enrollment_service(bootstrap_secret: str, *, display_name: str) -> EnrollmentResult:
        pepper = resolved_settings.device_watch_bootstrap_hmac_pepper
        return enroll_device(
            owned_engine(),
            bootstrap_secret,
            None if pepper is None else pepper.get_secret_value(),
            display_name=display_name,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        nonlocal engine
        if database_check is None:
            owned_engine()
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    setup_logging()
    app = FastAPI(
        title="Device Watch",
        version="0.1.0",
        docs_url="/api/docs" if resolved_settings.device_watch_enable_docs else None,
        redoc_url="/api/redoc" if resolved_settings.device_watch_enable_docs else None,
        openapi_url="/api/openapi.json" if resolved_settings.device_watch_enable_docs else None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.state.database_check = database_check or default_database_check
    app.state.enrollment_service = enrollment_service
    app.include_router(api_router)
    return app


__all__ = ["create_app"]
