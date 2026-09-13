"""Narrow enrollment endpoint with route-local, secret-safe error handling."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Protocol, cast

from fastapi import APIRouter, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException

from device_watch_server.api.enrollment_schemas import (
    EnrollmentFailure,
    EnrollmentRequest,
    EnrollmentResponse,
)
from device_watch_server.enrollment.transaction import EnrollmentError, EnrollmentResult


class EnrollmentService(Protocol):
    def __call__(
        self, bootstrap_secret: str, *, display_name: str
    ) -> EnrollmentResult: ...


def _failure(status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=EnrollmentFailure().model_dump(),
        headers={"Cache-Control": "no-store"},
    )


class EnrollmentRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def sanitized(request: Request) -> Response:
            try:
                return await original(request)
            except (RequestValidationError, EnrollmentError):
                return _failure(400)
            except HTTPException as error:
                # Malformed JSON/encoding can fail before Pydantic validation.
                return _failure(400 if error.status_code == 400 else 500)
            except Exception:  # noqa: BLE001 -- final secret-bearing HTTP error boundary
                # Response validation and unexpected errors can carry plaintext.
                # Never forward their detail, body, or traceback to logs or clients.
                return _failure(500)

        return sanitized


router = APIRouter(route_class=EnrollmentRoute)


@router.post(
    "/api/v1/enrollment",
    status_code=201,
    response_model=EnrollmentResponse,
    responses={
        400: {"model": EnrollmentFailure, "description": "Invalid enrollment request"},
        500: {
            "model": EnrollmentFailure,
            "description": "Enrollment could not complete",
        },
        # Override FastAPI's automatic detailed 422 schema for this secret boundary.
        "default": {
            "model": EnrollmentFailure,
            "description": "Sanitized enrollment failure",
        },
    },
)
def enroll(
    payload: EnrollmentRequest, request: Request, response: Response
) -> EnrollmentResponse:
    """Call the transaction in FastAPI's worker thread; return only committed output."""
    service = cast(EnrollmentService, request.app.state.enrollment_service)
    result = service(
        payload.bootstrap_secret.get_secret_value(), display_name=payload.display_name
    )
    response.headers["Cache-Control"] = "no-store"
    # agent_version is validated for protocol compatibility; latest-version state
    # belongs to the later heartbeat slice, not this identity transaction.
    return EnrollmentResponse(
        device_id=result.device.device_id,
        display_name=result.device.display_name,
        credential=result.credential.to_wire(),
        created_at=result.device.created_at,
    )
