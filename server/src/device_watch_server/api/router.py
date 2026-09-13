"""API router configuration for the Device Watch server."""

from __future__ import annotations

from fastapi import APIRouter

from device_watch_server.api.enrollment import router as enrollment_router
from device_watch_server.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(enrollment_router)

__all__ = ["api_router"]
