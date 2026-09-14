from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from device_watch_server.domain.contracts import (
    CURRENT_PROTOCOL_VERSION,
    BootstrapState,
    ConnectivityState,
    CredentialState,
    DeviceIdentity,
    DeviceLifecycle,
    DeviceSummary,
    HeartbeatRequest,
    HeartbeatStatus,
    PersistenceBoundary,
)

UTC_NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
DEVICE_ID = uuid4()
SUBMISSION_ID = uuid4()


def test_identity_requires_uuid4_and_normalizes_display_name_and_timestamp() -> None:
    identity = DeviceIdentity(
        device_id=DEVICE_ID,
        display_name="  Office workstation  ",
        created_at=UTC_NOW,
    )

    assert identity.device_id == DEVICE_ID
    assert identity.display_name == "Office workstation"
    assert identity.created_at == UTC_NOW
    assert identity.lifecycle is DeviceLifecycle.ACTIVE

    with pytest.raises(ValidationError, match="UUIDv4"):
        DeviceIdentity(
            device_id=UUID("00000000-0000-0000-0000-000000000001"),
            display_name="workstation",
            created_at=UTC_NOW,
        )


def test_identity_requires_bounded_non_blank_name_and_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        DeviceIdentity(device_id=DEVICE_ID, display_name="  ", created_at=UTC_NOW)

    with pytest.raises(ValidationError, match="timezone"):
        DeviceIdentity(
            device_id=DEVICE_ID,
            display_name="workstation",
            created_at=datetime.fromisoformat("2026-09-08T12:00:00"),
        )

    with pytest.raises(ValidationError):
        DeviceIdentity(
            device_id=DEVICE_ID,
            display_name="x" * 121,
            created_at=UTC_NOW,
        )


def test_summary_is_an_allowlisted_connectivity_contract() -> None:
    summary = DeviceSummary(
        device_id=DEVICE_ID,
        display_name="workstation",
        created_at=UTC_NOW,
        last_seen_at=UTC_NOW,
        agent_version="0.2.0",
        connectivity=ConnectivityState.ONLINE,
    )

    payload = summary.model_dump()
    assert payload == {
        "device_id": DEVICE_ID,
        "display_name": "workstation",
        "created_at": UTC_NOW,
        "lifecycle": DeviceLifecycle.ACTIVE,
        "last_seen_at": UTC_NOW,
        "agent_version": "0.2.0",
        "connectivity": ConnectivityState.ONLINE,
    }
    assert (
        not {"credential", "credential_hash", "bootstrap_secret", "metrics"}
        & payload.keys()
    )


def test_heartbeat_is_minimal_versioned_and_uses_aware_observation_time() -> None:
    heartbeat = HeartbeatRequest(
        protocol_version=1,
        submission_id=SUBMISSION_ID,
        agent_version=" 0.2.0 ",
        observed_at=UTC_NOW,
    )

    assert heartbeat.protocol_version == CURRENT_PROTOCOL_VERSION
    assert heartbeat.agent_version == "0.2.0"
    assert heartbeat.observed_at == UTC_NOW
    assert set(heartbeat.model_dump()) == {
        "protocol_version",
        "submission_id",
        "agent_version",
        "observed_at",
    }

    with pytest.raises(ValidationError, match="unsupported"):
        HeartbeatRequest(
            protocol_version=CURRENT_PROTOCOL_VERSION + 1,
            submission_id=SUBMISSION_ID,
            agent_version="0.2.0",
        )

    with pytest.raises(ValidationError, match="Extra inputs"):
        HeartbeatRequest(
            protocol_version=1,
            submission_id=SUBMISSION_ID,
            agent_version="0.2.0",
            cpu_percent=10,
        )


def test_persistence_boundary_contains_current_state_only() -> None:
    state = PersistenceBoundary(
        last_seen_at=UTC_NOW,
        last_heartbeat_submission_id=SUBMISSION_ID,
        last_agent_version="0.2.0",
    )
    assert state.last_seen_at == UTC_NOW
    assert state.last_heartbeat_submission_id == SUBMISSION_ID
    assert set(state.model_dump()) == {
        "last_seen_at",
        "last_heartbeat_submission_id",
        "last_agent_version",
    }

    with pytest.raises(ValidationError, match="requires last_seen_at"):
        PersistenceBoundary(last_heartbeat_submission_id=SUBMISSION_ID)


def test_stage2_state_enums_are_explicit_and_immutable() -> None:
    assert {state.value for state in BootstrapState} == {
        "available",
        "consumed",
        "expired",
        "revoked",
    }
    assert {state.value for state in CredentialState} == {
        "active",
        "revoked",
        "replaced",
    }
    assert {state.value for state in ConnectivityState} == {
        "never_seen",
        "online",
        "offline",
    }
    assert HeartbeatStatus.ACCEPTED.value == "accepted"

    heartbeat = HeartbeatRequest(
        protocol_version=1, submission_id=SUBMISSION_ID, agent_version="0.2.0"
    )
    with pytest.raises(ValidationError):
        heartbeat.agent_version = "changed"  # type: ignore[misc]


def test_utc_normalization_does_not_change_receipt_semantics() -> None:
    offset_timestamp = datetime(2026, 9, 8, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    identity = DeviceIdentity(
        device_id=DEVICE_ID,
        display_name="workstation",
        created_at=offset_timestamp,
    )
    assert identity.created_at == UTC_NOW
