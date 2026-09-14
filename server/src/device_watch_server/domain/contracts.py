"""Typed Stage 2 device-connectivity contracts.

These models intentionally contain no ORM mapping, transport, or credential secret.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

CURRENT_PROTOCOL_VERSION = 1
_HEARTBEAT_UUID_PATTERN = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_HEARTBEAT_TIMESTAMP_PATTERN = (
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
)


class DeviceLifecycle(StrEnum):
    """Server-owned lifecycle state for a device identity."""

    ACTIVE = "active"
    REVOKED = "revoked"


class BootstrapState(StrEnum):
    """Lifecycle state of operator-provisioned enrollment material."""

    AVAILABLE = "available"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CredentialState(StrEnum):
    """Lifecycle state of a device credential representation."""

    ACTIVE = "active"
    REVOKED = "revoked"
    REPLACED = "replaced"


class ConnectivityState(StrEnum):
    """Derived current connectivity state."""

    NEVER_SEEN = "never_seen"
    ONLINE = "online"
    OFFLINE = "offline"


class HeartbeatStatus(StrEnum):
    """Server response status for an accepted heartbeat."""

    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)


class ContractModel(BaseModel):
    """Base model enforcing strict fields and immutable contract instances."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DeviceIdentity(ContractModel):
    """Server-owned stable identity metadata without mutable machine identifiers."""

    device_id: UUID
    display_name: str = Field(min_length=1, max_length=120)
    created_at: datetime
    lifecycle: DeviceLifecycle = DeviceLifecycle.ACTIVE

    @field_validator("device_id")
    @classmethod
    def require_uuid4(cls, value: UUID) -> UUID:
        if value.version != 4:
            raise ValueError("device_id must be a UUIDv4")
        return value

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name must not be blank")
        return normalized

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _require_utc(value)


class DeviceSummary(DeviceIdentity):
    """Allowlisted device fields for future read APIs."""

    last_seen_at: datetime | None = None
    agent_version: str | None = Field(default=None, max_length=64)
    connectivity: ConnectivityState

    @field_validator("last_seen_at")
    @classmethod
    def normalize_last_seen_at(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_utc(value)


def _heartbeat_uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        parsed = UUID(value)
        if str(parsed) == value:
            return parsed
    raise ValueError("invalid heartbeat UUID")


def _heartbeat_timestamp(value: object) -> datetime:
    try:
        if isinstance(value, str) and re.fullmatch(_HEARTBEAT_TIMESTAMP_PATTERN, value):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise ValueError
        return _require_utc(value)
    except (ValueError, OverflowError):
        raise ValueError("invalid heartbeat timestamp") from None


class HeartbeatRequest(ContractModel):
    """Minimal heartbeat envelope; it contains no metrics or inventory."""

    model_config = ConfigDict(hide_input_in_errors=True)

    protocol_version: Literal[1] = Field(repr=False)
    submission_id: UUID = Field(
        repr=False, json_schema_extra={"pattern": _HEARTBEAT_UUID_PATTERN}
    )
    agent_version: str = Field(min_length=1, max_length=64, strict=True, repr=False)
    observed_at: datetime | None = Field(
        default=None,
        repr=False,
        json_schema_extra={"pattern": _HEARTBEAT_TIMESTAMP_PATTERN},
    )

    @field_validator("protocol_version", mode="before")
    @classmethod
    def require_current_protocol(cls, value: object) -> int:
        if type(value) is not int or value != CURRENT_PROTOCOL_VERSION:
            raise ValueError("unsupported protocol_version")
        return value

    @field_validator("submission_id", mode="before")
    @classmethod
    def require_submission_uuid(cls, value: object) -> UUID:
        return _heartbeat_uuid(value)

    @field_validator("agent_version")
    @classmethod
    def normalize_agent_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("agent_version must not be blank")
        return normalized

    @field_validator("observed_at", mode="before")
    @classmethod
    def normalize_observed_at(cls, value: object) -> datetime | None:
        return None if value is None else _heartbeat_timestamp(value)


class HeartbeatResponse(ContractModel):
    """Server receipt acknowledgement for an accepted heartbeat."""

    model_config = ConfigDict(hide_input_in_errors=True)

    protocol_version: Literal[1] = Field(repr=False)
    device_id: UUID4 = Field(
        repr=False,
        json_schema_extra={
            "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
    )
    received_at: datetime = Field(
        repr=False, json_schema_extra={"pattern": _HEARTBEAT_TIMESTAMP_PATTERN}
    )
    status: HeartbeatStatus = Field(repr=False)

    @field_validator("protocol_version", mode="before")
    @classmethod
    def require_current_protocol(cls, value: object) -> int:
        if type(value) is not int or value != CURRENT_PROTOCOL_VERSION:
            raise ValueError("unsupported protocol_version")
        return value

    @field_validator("device_id", mode="before")
    @classmethod
    def require_canonical_device_uuid(cls, value: object) -> UUID:
        return _heartbeat_uuid(value)

    @field_validator("received_at", mode="before")
    @classmethod
    def normalize_received_at(cls, value: object) -> datetime:
        return _heartbeat_timestamp(value)


class HeartbeatAccepted(HeartbeatResponse):
    """Convenience contract for a newly applied heartbeat."""

    status: Literal[HeartbeatStatus.ACCEPTED] = Field(
        default=HeartbeatStatus.ACCEPTED, repr=False
    )


class PersistenceBoundary(ContractModel):
    """Document the current-state fields allowed at the persistence boundary."""

    last_seen_at: datetime | None = None
    last_heartbeat_submission_id: UUID | None = None
    last_agent_version: str | None = Field(default=None, max_length=64)

    @field_validator("last_seen_at")
    @classmethod
    def normalize_last_seen_at(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_utc(value)

    @model_validator(mode="after")
    def require_submission_with_timestamp(self) -> Self:
        if self.last_heartbeat_submission_id is not None and self.last_seen_at is None:
            raise ValueError("submission identity requires last_seen_at")
        return self


__all__ = [
    "CURRENT_PROTOCOL_VERSION",
    "BootstrapState",
    "ConnectivityState",
    "CredentialState",
    "DeviceIdentity",
    "DeviceLifecycle",
    "DeviceSummary",
    "HeartbeatAccepted",
    "HeartbeatRequest",
    "HeartbeatResponse",
    "HeartbeatStatus",
    "PersistenceBoundary",
]
