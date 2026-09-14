"""Step 09 wire contracts and pure current-state idempotency decisions."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from device_watch_server.domain.contracts import (
    HeartbeatAccepted,
    HeartbeatRequest,
    HeartbeatResponse,
    HeartbeatStatus,
    PersistenceBoundary,
)
from device_watch_server.domain.heartbeat import (
    HeartbeatError,
    HeartbeatFailure,
    decide_heartbeat,
    parse_heartbeat_request,
    parse_heartbeat_response,
)

DEVICE = UUID("12345678-1234-4234-8234-123456789abc")
SUBMISSION = UUID("22345678-1234-4234-8234-123456789abc")
NEXT_SUBMISSION = UUID("32345678-1234-4234-8234-123456789abc")
RECEIVED = datetime(2026, 9, 14, 12, tzinfo=UTC)


def request_body() -> dict[str, object]:
    return {
        "protocol_version": 1,
        "submission_id": str(SUBMISSION),
        "agent_version": "0.2.0",
    }


def response_body() -> dict[str, object]:
    return {
        "protocol_version": 1,
        "device_id": str(DEVICE),
        "received_at": "2026-09-14T12:00:00Z",
        "status": "accepted",
    }


def test_request_and_response_roundtrip_exact_minimal_json() -> None:
    request = parse_heartbeat_request(json.dumps(request_body()))
    assert request.model_dump(mode="json", exclude_none=True) == request_body()
    assert request.observed_at is None
    response = parse_heartbeat_response(json.dumps(response_body()))
    assert response.model_dump(mode="json") == response_body()
    assert response.received_at == RECEIVED
    assert response.status is HeartbeatStatus.ACCEPTED


@pytest.mark.parametrize("model", [HeartbeatRequest, HeartbeatResponse])
@pytest.mark.parametrize("version", [True, 1.0, "1", None, -1, 0, 2])
def test_protocol_version_is_exact_integer_one(
    model: type[HeartbeatRequest] | type[HeartbeatResponse], version: object
) -> None:
    payload = request_body() if model is HeartbeatRequest else response_body()
    payload["protocol_version"] = version
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("model", [HeartbeatRequest, HeartbeatResponse])
def test_missing_protocol_version_is_rejected(
    model: type[HeartbeatRequest] | type[HeartbeatResponse],
) -> None:
    payload = request_body() if model is HeartbeatRequest else response_body()
    del payload["protocol_version"]
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "field",
    [
        "device_id",
        "credential",
        "bootstrap_secret",
        "authorization",
        "metrics",
        "cpu_percent",
        "inventory",
        "hostname",
        "ip_address",
        "mac_address",
        "history",
    ],
)
def test_request_forbids_credentials_identity_metrics_and_inventory(field: str) -> None:
    payload = request_body()
    payload[field] = "synthetic-sensitive-value"
    with pytest.raises(HeartbeatError, match="^Heartbeat failed$") as caught:
        parse_heartbeat_request(json.dumps(payload))
    assert "synthetic-sensitive-value" not in str(caught.value)


@pytest.mark.parametrize(
    "submission", ["invalid", "22345678123442348234123456789abc", 42, None]
)
def test_submission_requires_canonical_uuid_string(submission: object) -> None:
    payload = request_body()
    payload["submission_id"] = submission
    with pytest.raises(HeartbeatError):
        parse_heartbeat_request(json.dumps(payload))


def test_submission_uuid_version_is_not_restricted_to_device_uuid4() -> None:
    payload = request_body()
    payload["submission_id"] = "22345678-1234-1234-8234-123456789abc"
    request = parse_heartbeat_request(json.dumps(payload))
    assert str(request.submission_id) == payload["submission_id"]


@pytest.mark.parametrize("version", ["", "  ", "x" * 65, 1, True, None])
def test_agent_version_requires_bounded_nonblank_text(version: object) -> None:
    payload = request_body()
    payload["agent_version"] = version
    with pytest.raises(HeartbeatError):
        parse_heartbeat_request(json.dumps(payload))


@pytest.mark.parametrize("value", [None, "2026-09-14T14:00:00+02:00"])
def test_optional_observation_is_normalized_to_utc(value: str | None) -> None:
    payload = request_body()
    payload["observed_at"] = value
    request = parse_heartbeat_request(json.dumps(payload))
    assert request.observed_at == (None if value is None else RECEIVED)


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-14T12:00:00",
        "2026-09-14",
        "not-a-time",
        12345,
        True,
        "2026-09-14T12:00:00+00:60",
        "0001-01-01T00:00:00+01:00",
    ],
)
@pytest.mark.parametrize("response", [False, True])
def test_timestamps_reject_naive_numeric_invalid_and_overflowing_values(
    value: object, response: bool
) -> None:
    payload = response_body() if response else request_body()
    payload["received_at" if response else "observed_at"] = value
    parser = parse_heartbeat_response if response else parse_heartbeat_request
    with pytest.raises(HeartbeatError):
        parser(json.dumps(payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "invalid"),
        ("status", None),
        ("device_id", "12345678-1234-1234-8234-123456789abc"),
        ("received_at", None),
        ("credential", "synthetic-sensitive-value"),
        ("metrics", {}),
    ],
)
def test_response_rejects_invalid_status_identity_receipt_and_extra_fields(
    field: str, value: object
) -> None:
    payload = response_body()
    payload[field] = value
    with pytest.raises(HeartbeatError):
        parse_heartbeat_response(json.dumps(payload))


def test_accepted_convenience_model_cannot_claim_duplicate() -> None:
    payload = response_body()
    payload["status"] = "duplicate"
    with pytest.raises(ValidationError):
        HeartbeatAccepted.model_validate(payload)


@pytest.mark.parametrize("raw", ["{", "[]", "null", "{}", b"\xff"])
def test_wire_errors_are_sanitized_without_logging_input(
    raw: str | bytes, caplog: pytest.LogCaptureFixture
) -> None:
    with pytest.raises(HeartbeatError, match="^Heartbeat failed$"):
        parse_heartbeat_request(raw)
    assert caplog.records == []
    assert HeartbeatFailure().model_dump(mode="json") == {"detail": "Heartbeat failed"}


def test_failure_response_cannot_carry_diagnostics() -> None:
    with pytest.raises(ValidationError):
        HeartbeatFailure.model_validate({"detail": "synthetic-sensitive-value"})
    with pytest.raises(ValidationError):
        HeartbeatFailure.model_validate({"detail": "Heartbeat failed", "input": "data"})


def test_json_schemas_record_exact_fields_required_values_and_formats() -> None:
    request = HeartbeatRequest.model_json_schema()
    response = HeartbeatResponse.model_json_schema()
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "protocol_version",
        "submission_id",
        "agent_version",
    }
    assert set(request["properties"]) == {
        "protocol_version",
        "submission_id",
        "agent_version",
        "observed_at",
    }
    assert request["properties"]["protocol_version"]["const"] == 1
    assert request["properties"]["submission_id"]["format"] == "uuid"
    assert request["properties"]["agent_version"]["maxLength"] == 64
    assert response["additionalProperties"] is False
    assert set(response["required"]) == {
        "protocol_version",
        "device_id",
        "received_at",
        "status",
    }
    assert set(response["properties"]) == set(response["required"])


def test_first_receipt_uses_server_time_and_produces_only_current_state() -> None:
    payload = request_body()
    payload["observed_at"] = "2099-01-01T00:00:00Z"
    decision = decide_heartbeat(
        parse_heartbeat_request(json.dumps(payload)),
        device_id=DEVICE,
        received_at=RECEIVED,
        current=PersistenceBoundary(),
    )
    assert decision.apply_update
    assert decision.next_state.model_dump() == {
        "last_seen_at": RECEIVED,
        "last_heartbeat_submission_id": SUBMISSION,
        "last_agent_version": "0.2.0",
    }
    assert decision.response.model_dump(mode="json") == response_body()


def test_repeated_latest_id_does_not_refresh_time_or_change_version() -> None:
    current = PersistenceBoundary(
        last_seen_at=RECEIVED,
        last_heartbeat_submission_id=SUBMISSION,
        last_agent_version="0.2.0",
    )
    payload = request_body()
    payload["agent_version"] = "different-but-valid"
    payload["observed_at"] = "2099-01-01T00:00:00Z"
    retry_time = RECEIVED + timedelta(seconds=20)
    decision = decide_heartbeat(
        parse_heartbeat_request(json.dumps(payload)),
        device_id=DEVICE,
        received_at=retry_time,
        current=current,
    )
    assert not decision.apply_update
    assert decision.next_state == current
    assert decision.response.status is HeartbeatStatus.DUPLICATE
    assert decision.response.received_at == retry_time


@pytest.mark.parametrize("offset", [-30, 0, 30])
def test_distinct_id_never_moves_last_seen_backwards(offset: int) -> None:
    current = PersistenceBoundary(
        last_seen_at=RECEIVED,
        last_heartbeat_submission_id=SUBMISSION,
        last_agent_version="0.1.0",
    )
    payload = request_body()
    payload["submission_id"] = str(NEXT_SUBMISSION)
    receipt_time = RECEIVED + timedelta(seconds=offset)
    decision = decide_heartbeat(
        parse_heartbeat_request(json.dumps(payload)),
        device_id=DEVICE,
        received_at=receipt_time,
        current=current,
    )
    assert decision.apply_update
    assert decision.next_state.last_seen_at == (
        receipt_time if offset > 0 else RECEIVED
    )
    assert decision.next_state.last_heartbeat_submission_id == NEXT_SUBMISSION
    assert decision.next_state.last_agent_version == "0.2.0"
    assert decision.response.received_at == receipt_time
    assert decision.response.status is HeartbeatStatus.ACCEPTED


def test_retention_is_only_latest_id_and_not_a_global_submission_key() -> None:
    request = parse_heartbeat_request(json.dumps(request_body()))
    current = PersistenceBoundary(
        last_seen_at=RECEIVED,
        last_heartbeat_submission_id=NEXT_SUBMISSION,
        last_agent_version="0.2.0",
    )
    older = decide_heartbeat(
        request,
        device_id=DEVICE,
        received_at=RECEIVED,
        current=current,
    )
    other_device = UUID("42345678-1234-4234-8234-123456789abc")
    independent = decide_heartbeat(
        request,
        device_id=other_device,
        received_at=RECEIVED,
        current=PersistenceBoundary(),
    )
    assert older.response.status is HeartbeatStatus.ACCEPTED
    assert independent.response.status is HeartbeatStatus.ACCEPTED
    assert independent.response.device_id == other_device


def test_decision_requires_aware_server_receipt_time() -> None:
    request = parse_heartbeat_request(json.dumps(request_body()))
    with pytest.raises(HeartbeatError):
        decide_heartbeat(
            request,
            device_id=DEVICE,
            received_at=datetime(2026, 9, 14, 12),
            current=PersistenceBoundary(),
        )
