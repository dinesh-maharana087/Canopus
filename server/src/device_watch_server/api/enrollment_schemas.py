"""Version-one enrollment wire models, separate from persistence records."""

from __future__ import annotations

from typing import Literal

from pydantic import (
    UUID4,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
)

from device_watch_server.enrollment.bootstrap import BootstrapValue


class EnrollmentRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )

    protocol_version: Literal[1]
    bootstrap_secret: SecretStr = Field(min_length=50, max_length=50)
    display_name: str = Field(min_length=1, max_length=120, repr=False)
    agent_version: str = Field(min_length=1, max_length=64, repr=False)

    @field_validator("protocol_version", mode="before")
    @classmethod
    def require_protocol_one(cls, value: object) -> object:
        # Literal equality alone would admit True or 1.0 as protocol version 1.
        if type(value) is not int or value != 1:
            raise ValueError("Enrollment failed")
        return value

    @field_validator("bootstrap_secret")
    @classmethod
    def require_canonical_bootstrap(cls, value: SecretStr) -> SecretStr:
        BootstrapValue.parse(value.get_secret_value())
        return value

    @field_validator("display_name", "agent_version")
    @classmethod
    def normalize_nonblank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Enrollment failed")
        return normalized


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    protocol_version: Literal[1] = 1
    device_id: UUID4
    display_name: str = Field(min_length=1, max_length=120, repr=False)
    credential: str = Field(min_length=83, max_length=83, repr=False)
    created_at: AwareDatetime


class EnrollmentFailure(BaseModel):
    detail: Literal["Enrollment failed"] = "Enrollment failed"
