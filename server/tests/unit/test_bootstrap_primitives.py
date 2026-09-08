from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from device_watch_server.domain.contracts import BootstrapState
from device_watch_server.enrollment.bootstrap import (
    DIGEST_VERSION,
    BootstrapLifecycle,
    BootstrapValue,
    bootstrap_digest,
    bootstrap_fingerprint,
    generate_bootstrap_value,
    verify_bootstrap_digest,
)

PEPPER = "p" * 32
NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


def test_generated_value_is_a_strict_32_byte_unpadded_base64url_wire_value() -> None:
    value = generate_bootstrap_value()

    wire_value = value.to_wire()
    assert wire_value.startswith("dwb_v1_")
    assert "=" not in wire_value
    assert BootstrapValue.parse(wire_value) == value
    assert len(value.payload) == 32


@pytest.mark.parametrize(
    "wire_value",
    (
        "dwb_v2_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        "dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA+",
        "dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    ),
)
def test_parser_rejects_malformed_or_wrong_length_values(wire_value: str) -> None:
    with pytest.raises(ValueError) as error:
        BootstrapValue.parse(wire_value)

    assert wire_value not in str(error.value)


def test_fingerprint_and_digest_are_separate_32_byte_versioned_values() -> None:
    value = BootstrapValue.parse("dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

    fingerprint = bootstrap_fingerprint(value)
    digest = bootstrap_digest(value, PEPPER)

    assert len(fingerprint) == 32
    assert len(digest) == 32
    assert fingerprint != digest
    assert DIGEST_VERSION == "hmac-sha256-v1"


def test_digest_verification_accepts_only_the_matching_value_and_pepper() -> None:
    value = BootstrapValue.parse("dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    other_value = BootstrapValue.parse(
        "dwb_v1_AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE"
    )
    digest = bootstrap_digest(value, PEPPER)

    assert verify_bootstrap_digest(value, digest, PEPPER)
    assert not verify_bootstrap_digest(other_value, digest, PEPPER)
    assert not verify_bootstrap_digest(value, digest, "q" * 32)


@pytest.mark.parametrize("pepper", ("p" * 31, "\u20ac" * 10))
def test_digest_operations_require_at_least_32_utf8_pepper_bytes(pepper: str) -> None:
    value = BootstrapValue.parse("dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

    with pytest.raises(ValueError):
        bootstrap_digest(value, pepper)


def test_plaintext_carrier_never_exposes_its_wire_value_in_repr_or_str() -> None:
    value = BootstrapValue.parse("dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    wire_value = value.to_wire()

    assert wire_value not in repr(value)
    assert wire_value not in str(value)


def test_lifecycle_derives_available_and_exact_expiry_from_utc_timestamps() -> None:
    lifecycle = BootstrapLifecycle(
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )

    assert lifecycle.state_at(NOW) is BootstrapState.AVAILABLE
    assert lifecycle.state_at(NOW + timedelta(minutes=15)) is BootstrapState.EXPIRED
    assert lifecycle.state_at(NOW + timedelta(minutes=16)) is BootstrapState.EXPIRED


def test_lifecycle_treats_consumed_and_revoked_as_terminal_and_exclusive() -> None:
    consumed = BootstrapLifecycle(
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        consumed_at=NOW + timedelta(minutes=1),
    )
    revoked = BootstrapLifecycle(
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        revoked_at=NOW + timedelta(minutes=1),
    )

    assert consumed.state_at(NOW) is BootstrapState.CONSUMED
    assert revoked.state_at(NOW) is BootstrapState.REVOKED
    with pytest.raises(ValueError):
        BootstrapLifecycle(
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
            consumed_at=NOW,
            revoked_at=NOW,
        )


def test_lifecycle_normalizes_aware_timestamps_and_rejects_naive_timestamps() -> None:
    lifecycle = BootstrapLifecycle(
        created_at=datetime(2026, 9, 8, 14, 0, tzinfo=timezone(timedelta(hours=2))),
        expires_at=datetime(2026, 9, 8, 14, 15, tzinfo=timezone(timedelta(hours=2))),
    )

    assert lifecycle.created_at == NOW
    assert lifecycle.expires_at == NOW + timedelta(minutes=15)
    with pytest.raises(ValueError):
        BootstrapLifecycle(
            created_at=NOW.replace(tzinfo=None),
            expires_at=NOW + timedelta(minutes=15),
        )
