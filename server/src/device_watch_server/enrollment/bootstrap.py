"""Secret-safe cryptography and lifecycle primitives for enrollment bootstraps."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from device_watch_server.domain.contracts import BootstrapState

BOOTSTRAP_PREFIX = "dwb_v1_"
DIGEST_VERSION = "hmac-sha256-v1"
_BOOTSTRAP_BYTES = 32
_FINGERPRINT_DOMAIN = b"device-watch/bootstrap-fingerprint/v1\x00"
_DIGEST_DOMAIN = b"device-watch/bootstrap-digest/v1\x00"
_BASE64URL = re.compile(r"[A-Za-z0-9_-]+\Z")


def _invalid_value() -> ValueError:
    return ValueError("invalid bootstrap value")


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)


def _require_pepper(pepper: str) -> bytes:
    if not isinstance(pepper, str):
        raise TypeError("invalid bootstrap pepper")
    encoded = pepper.encode("utf-8")
    if len(encoded) < _BOOTSTRAP_BYTES:
        raise ValueError("bootstrap pepper must contain at least 32 UTF-8 bytes")
    return encoded


@dataclass(frozen=True, repr=False)
class BootstrapValue:
    """A plaintext bootstrap value whose default representations do not expose it."""

    payload: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.payload, bytes) or len(self.payload) != _BOOTSTRAP_BYTES:
            raise _invalid_value()

    def __repr__(self) -> str:
        return "BootstrapValue(<redacted>)"

    __str__ = __repr__

    @classmethod
    def parse(cls, wire_value: str) -> BootstrapValue:
        """Parse the only accepted bootstrap wire format without echoing it on error."""
        if not isinstance(wire_value, str) or not wire_value.startswith(BOOTSTRAP_PREFIX):
            raise _invalid_value()
        encoded_payload = wire_value.removeprefix(BOOTSTRAP_PREFIX)
        if not _BASE64URL.fullmatch(encoded_payload) or "=" in encoded_payload:
            raise _invalid_value()
        try:
            payload = base64.b64decode(
                encoded_payload + "=" * (-len(encoded_payload) % 4),
                altchars=b"-_",
                validate=True,
            )
        except (ValueError, binascii.Error):
            raise _invalid_value() from None
        return cls(payload)

    def to_wire(self) -> str:
        """Return the plaintext wire value only at an explicit trusted boundary."""
        encoded_payload = base64.urlsafe_b64encode(self.payload).decode("ascii")
        return BOOTSTRAP_PREFIX + encoded_payload.rstrip("=")


def generate_bootstrap_value() -> BootstrapValue:
    """Generate a bootstrap plaintext from exactly 32 cryptographically random bytes."""
    return BootstrapValue(secrets.token_bytes(_BOOTSTRAP_BYTES))


def bootstrap_fingerprint(value: BootstrapValue) -> bytes:
    """Return the versioned, domain-separated lookup fingerprint."""
    return hashlib.sha256(_FINGERPRINT_DOMAIN + value.payload).digest()


def bootstrap_digest(value: BootstrapValue, pepper: str) -> bytes:
    """Return the versioned, domain-separated HMAC digest for secure storage."""
    return hmac.digest(_require_pepper(pepper), _DIGEST_DOMAIN + value.payload, "sha256")


def verify_bootstrap_digest(value: BootstrapValue, digest: bytes, pepper: str) -> bool:
    """Verify a stored digest in constant time after validating its expected shape."""
    if not isinstance(digest, bytes) or len(digest) != _BOOTSTRAP_BYTES:
        return False
    return hmac.compare_digest(bootstrap_digest(value, pepper), digest)


@dataclass(frozen=True)
class BootstrapLifecycle:
    """Timestamp-only bootstrap lifecycle representation without a persisted state field."""

    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        created_at = _require_utc(self.created_at)
        expires_at = _require_utc(self.expires_at)
        consumed_at = None if self.consumed_at is None else _require_utc(self.consumed_at)
        revoked_at = None if self.revoked_at is None else _require_utc(self.revoked_at)
        if expires_at <= created_at:
            raise ValueError("bootstrap expiry must be after creation")
        if consumed_at is not None and revoked_at is not None:
            raise ValueError("bootstrap cannot be consumed and revoked")
        if consumed_at is not None and consumed_at < created_at:
            raise ValueError("bootstrap consumption cannot precede creation")
        if revoked_at is not None and revoked_at < created_at:
            raise ValueError("bootstrap revocation cannot precede creation")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "consumed_at", consumed_at)
        object.__setattr__(self, "revoked_at", revoked_at)

    def state_at(self, now: datetime) -> BootstrapState:
        """Derive the current lifecycle state, preserving terminal transitions."""
        if self.consumed_at is not None:
            return BootstrapState.CONSUMED
        if self.revoked_at is not None:
            return BootstrapState.REVOKED
        if _require_utc(now) >= self.expires_at:
            return BootstrapState.EXPIRED
        return BootstrapState.AVAILABLE


__all__ = [
    "BOOTSTRAP_PREFIX",
    "DIGEST_VERSION",
    "BootstrapLifecycle",
    "BootstrapValue",
    "bootstrap_digest",
    "bootstrap_fingerprint",
    "generate_bootstrap_value",
    "verify_bootstrap_digest",
]
