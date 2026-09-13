"""Device credentials with explicit plaintext and hash persistence boundaries."""

from __future__ import annotations

import base64
import binascii
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from argon2 import PasswordHasher, Type
from argon2.exceptions import HashingError, InvalidHashError, VerificationError

from device_watch_server.domain.contracts import CredentialState

_WIRE_PREFIX = "dwc_v1_"
_KEY_ID = re.compile(r"[0-9a-f]{32}")
_WIRE = re.compile(r"dwc_v1_([0-9a-f]{32})_([A-Za-z0-9_-]{43})")
_ENCODED_HASH = re.compile(
    r"\$argon2id\$v=19\$m=65536,t=3,p=4\$([A-Za-z0-9+/]{22})\$([A-Za-z0-9+/]{43})"
)
# RFC 9106 low-memory profile, explicitly pinned independently of library defaults.
_HASHER = PasswordHasher(
    type=Type.ID,
    memory_cost=65536,
    time_cost=3,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)
Clock = Callable[[], datetime]


class CredentialError(ValueError):
    """Generic error safe to map at a later operator or transport boundary."""

    def __init__(self) -> None:
        super().__init__("Credential operation failed")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CredentialError()
    return value.astimezone(UTC)


def _valid_key_id(value: str) -> bool:
    return isinstance(value, str) and _KEY_ID.fullmatch(value) is not None


def _decode(encoded: str, length: int, *, url_safe: bool) -> bytes:
    alphabet = b"-_" if url_safe else None
    try:
        decoded = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4), altchars=alphabet, validate=True
        )
    except (ValueError, binascii.Error):
        raise CredentialError() from None
    canonical = base64.b64encode(decoded, altchars=alphabet).decode("ascii").rstrip("=")
    if len(decoded) != length or canonical != encoded:
        raise CredentialError()
    return decoded


@dataclass(frozen=True, repr=False)
class CredentialValue:
    """Transient secret carrier. Only to_wire explicitly exposes the credential."""

    key_id: str
    secret: bytes

    def __post_init__(self) -> None:
        if not _valid_key_id(self.key_id):
            raise CredentialError()
        if not isinstance(self.secret, bytes) or len(self.secret) != 32:
            raise CredentialError()

    def __repr__(self) -> str:
        return "CredentialValue(<redacted>)"

    __str__ = __repr__

    @classmethod
    def parse(cls, wire_value: str) -> CredentialValue:
        """Parse a bounded, versioned, canonical URL-safe credential."""
        if not isinstance(wire_value, str) or len(wire_value) != 83:
            raise CredentialError()
        matched = _WIRE.fullmatch(wire_value)
        if matched is None:
            raise CredentialError()
        return cls(matched[1], _decode(matched[2], 32, url_safe=True))

    def to_wire(self) -> str:
        secret = base64.urlsafe_b64encode(self.secret).decode("ascii").rstrip("=")
        return f"{_WIRE_PREFIX}{self.key_id}_{secret}"


@dataclass(frozen=True, repr=False)
class CredentialRecord:
    """Persistence input with no plaintext or device identity; hashes are not DTOs."""

    key_id: str
    secret_hash: str
    created_at: datetime
    revoked_at: datetime | None = None
    replaced_at: datetime | None = None

    def __post_init__(self) -> None:
        if not _valid_key_id(self.key_id) or not isinstance(self.secret_hash, str):
            raise CredentialError()
        created = _utc(self.created_at)
        revoked = None if self.revoked_at is None else _utc(self.revoked_at)
        replaced = None if self.replaced_at is None else _utc(self.replaced_at)
        if revoked is not None and revoked < created:
            raise CredentialError()
        if replaced is not None and (revoked is None or replaced != revoked):
            raise CredentialError()
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "revoked_at", revoked)
        object.__setattr__(self, "replaced_at", replaced)

    @property
    def state(self) -> CredentialState:
        if self.replaced_at is not None:
            return CredentialState.REPLACED
        if self.revoked_at is not None:
            return CredentialState.REVOKED
        return CredentialState.ACTIVE

    def __repr__(self) -> str:
        return f"CredentialRecord(key_id={self.key_id!r}, state={self.state.value!r}, hash=<redacted>)"

    __str__ = __repr__


@dataclass(frozen=True)
class IssuedCredential:
    """Plaintext delivery and persistence inputs kept separate, with masked reprs."""

    value: CredentialValue
    record: CredentialRecord


@dataclass(frozen=True)
class CredentialRotation:
    """Caller must persist BOTH records atomically before delivering replacement."""

    previous: CredentialRecord
    replacement: IssuedCredential


def hash_credential(
    value: CredentialValue, *, created_at: datetime
) -> CredentialRecord:
    """Hash only the secret, with a fresh library-generated cryptographic salt."""
    created = _utc(created_at)
    try:
        encoded = _HASHER.hash(value.secret)
    except (HashingError, ValueError):
        raise CredentialError() from None
    return CredentialRecord(value.key_id, encoded, created)


def issue_credential(*, clock: Clock = _utc_now) -> IssuedCredential:
    """Create independent 128-bit lookup and 256-bit secret values, without writes."""
    created = _utc(clock())
    value = CredentialValue(secrets.token_bytes(16).hex(), secrets.token_bytes(32))
    return IssuedCredential(value, hash_credential(value, created_at=created))


def _supported_hash(encoded: str) -> bool:
    # Native verification trusts encoded cost parameters. Bound and validate them
    # before any allocation; neither weaker nor more expensive profiles are accepted.
    if len(encoded) != 97:
        return False
    matched = _ENCODED_HASH.fullmatch(encoded)
    if matched is None:
        return False
    try:
        _decode(matched[1], 16, url_safe=False)
        _decode(matched[2], 32, url_safe=False)
    except CredentialError:
        return False
    return True


def verify_credential(wire_value: str, record: CredentialRecord | None) -> bool:
    """Fail closed; secret comparison belongs to Argon2's native verifier.

    Parsing, public-ID mismatch, and terminal-state rejection may return early.
    This is not an equal-time guarantee for a future HTTP request or DB lookup.
    """
    try:
        value = CredentialValue.parse(wire_value)
    except CredentialError:
        return False
    if (
        record is None
        or record.state is not CredentialState.ACTIVE
        or value.key_id != record.key_id
        or not _supported_hash(record.secret_hash)
    ):
        return False
    try:
        return _HASHER.verify(record.secret_hash, value.secret)
    except (VerificationError, InvalidHashError):
        return False


def _transition_time(record: CredentialRecord, value: datetime) -> datetime:
    now = _utc(value)
    if record.state is not CredentialState.ACTIVE or now < record.created_at:
        raise CredentialError()
    return now


def revoke_credential(
    record: CredentialRecord, *, revoked_at: datetime
) -> CredentialRecord:
    """Return a terminal revocation value; persistence remains caller-owned."""
    now = _transition_time(record, revoked_at)
    return replace(record, revoked_at=now)


def rotate_credential(
    record: CredentialRecord, *, clock: Clock = _utc_now
) -> CredentialRotation:
    """Prepare replacement issuance and old-key revocation without committing either."""
    now = _transition_time(record, clock())
    replacement = issue_credential(clock=lambda: now)
    return CredentialRotation(
        previous=replace(record, revoked_at=now, replaced_at=now),
        replacement=replacement,
    )
