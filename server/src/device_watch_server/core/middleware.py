"""Middleware for structured request logging."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("device_watch_server.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request metadata without emitting secrets or request bodies."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        path = request.url.path
        method = request.method
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            logger.info(
                "request complete",
                extra={
                    "event": "http_request",
                    "method": method,
                    "path": path,
                    "normalized_path": path,
                    "status": status_code,
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                },
            )
            return response
        except Exception:
            logger.warning(
                "request failed",
                extra={
                    "event": "http_request",
                    "method": method,
                    "path": path,
                    "normalized_path": path,
                    "status": status_code,
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                },
            )
            raise


__all__ = ["RequestLoggingMiddleware"]
