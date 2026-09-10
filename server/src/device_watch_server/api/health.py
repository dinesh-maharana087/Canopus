"""Health endpoints for liveness and readiness checks."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("device_watch_server.api.health")


class HealthResponse(BaseModel):
    """Structured health status payload."""

    status: Literal["ok", "unavailable"]


@router.get("/api/v1/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    """Return process liveness without touching the database."""

    return HealthResponse(status="ok")


@router.get("/api/v1/health/ready", response_model=HealthResponse)
def ready(request: Request) -> HealthResponse | JSONResponse:
    """Return readiness based on the dependency check result."""

    database_check = request.app.state.database_check
    try:
        database_check()
    except RuntimeError:
        logger.warning(
            "database readiness failed",
            extra={"event": "database_readiness_failed"},
        )
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return HealthResponse(status="ok")
