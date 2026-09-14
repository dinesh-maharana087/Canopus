"""Heartbeat v1 decoding and pure idempotency rules; no I/O or authentication.

The future service must authenticate first and supply the current state for that
device. It must apply a decision atomically with the state it read. Only the
latest submission ID is retained, until replaced by a different ID; there is no
TTL or history. Retries of that latest ID do not change state, even when the
validated body differs. Older IDs outside that slot are treated as new.

Receipt acknowledgements use this attempt's server time, while last_seen_at is
monotonic. Observation time never participates in either decision or last-seen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict

from device_watch_server.domain.contracts import (
    ContractModel,
    HeartbeatRequest,
    HeartbeatResponse,
    HeartbeatStatus,
    PersistenceBoundary,
)


class HeartbeatError(ValueError):
    """Public decoding/decision error without payload or validation diagnostics."""

    def __init__(self) -> None:
        super().__init__("Heartbeat failed")


class HeartbeatFailure(ContractModel):
    """Same opaque error body for validation, authentication and service failures."""

    model_config = ConfigDict(hide_input_in_errors=True)

    detail: Literal["Heartbeat failed"] = "Heartbeat failed"


def parse_heartbeat_request(payload: str | bytes) -> HeartbeatRequest:
    """Validate an untrusted JSON body without exposing Pydantic input errors."""
    try:
        return HeartbeatRequest.model_validate_json(payload)
    except (ValueError, TypeError):
        raise HeartbeatError() from None


def parse_heartbeat_response(payload: str | bytes) -> HeartbeatResponse:
    """Validate a receipt acknowledgement using the same public error boundary."""
    try:
        return HeartbeatResponse.model_validate_json(payload)
    except (ValueError, TypeError):
        raise HeartbeatError() from None


@dataclass(frozen=True, slots=True)
class HeartbeatDecision:
    """A value-only decision for the later authenticated persistence service."""

    response: HeartbeatResponse
    next_state: PersistenceBoundary
    apply_update: bool


def decide_heartbeat(
    request: HeartbeatRequest,
    *,
    device_id: UUID,
    received_at: datetime,
    current: PersistenceBoundary,
) -> HeartbeatDecision:
    """Decide duplicate/new semantics for one authenticated device's current state.

    A duplicate preserves all fields; its response is not a cached byte replay.
    New submissions use max(previous last-seen, normalized server receipt).
    Authentication and atomic persistence are caller obligations, not performed
    by this pure contract function.
    """
    try:
        duplicate = current.last_heartbeat_submission_id == request.submission_id
        response = HeartbeatResponse(
            protocol_version=1,
            device_id=device_id,
            received_at=received_at,
            status=HeartbeatStatus.DUPLICATE if duplicate else HeartbeatStatus.ACCEPTED,
        )
        if duplicate:
            return HeartbeatDecision(
                response=response, next_state=current, apply_update=False
            )
        last_seen = response.received_at
        if current.last_seen_at is not None:
            last_seen = max(current.last_seen_at, last_seen)
        next_state = PersistenceBoundary(
            last_seen_at=last_seen,
            last_heartbeat_submission_id=request.submission_id,
            last_agent_version=request.agent_version,
        )
        return HeartbeatDecision(
            response=response, next_state=next_state, apply_update=True
        )
    except (ValueError, TypeError, OverflowError):
        raise HeartbeatError() from None


__all__ = [
    "HeartbeatDecision",
    "HeartbeatError",
    "HeartbeatFailure",
    "decide_heartbeat",
    "parse_heartbeat_request",
    "parse_heartbeat_response",
]
