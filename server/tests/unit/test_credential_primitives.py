"""Device credential security contracts without database or transport wiring."""

from __future__ import annotations

import logging
import re
import secrets
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from typing import cast

import pytest
from argon2 import Type, extract_parameters
from argon2.exceptions import HashingError, VerificationError

from device_watch_server.auth import credentials
from device_watch_server.auth.credentials import (
    CredentialError,
    CredentialRecord,
    CredentialValue,
    IssuedCredential,
    hash_credential,
    issue_credential,
    revoke_credential,
    rotate_credential,
    verify_credential,
)
from device_watch_server.domain.contracts import CredentialState

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def issued() -> IssuedCredential:
    return issue_credential(clock=lambda: NOW)


def test_issuance_uses_independent_secure_random_id_and_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[int] = []
    random_bytes = secrets.token_bytes

    def recording_random(length: int) -> bytes:
        requested.append(length)
        return random_bytes(length)

    monkeypatch.setattr(secrets, "token_bytes", recording_random)
    results = [issue_credential(clock=lambda: NOW) for _ in range(3)]
    assert requested == [16, 32] * 3
    assert len({result.record.key_id for result in results}) == 3
    assert len({result.value.secret for result in results}) == 3
    for result in results:
        correct_format = (
            re.fullmatch(
                r"dwc_v1_[0-9a-f]{32}_[A-Za-z0-9_-]{43}", result.value.to_wire()
            )
            is not None
        )
        assert correct_format
        assert len(result.value.secret) == 32
        assert result.value.key_id == result.record.key_id
        assert verify_credential(result.value.to_wire(), result.record)


def test_argon2id_profile_and_fresh_salts_are_explicit(
    issued: IssuedCredential,
) -> None:
    second = hash_credential(issued.value, created_at=NOW)
    params = extract_parameters(second.secret_hash)
    assert (params.type, params.version) == (Type.ID, 19)
    assert (params.memory_cost, params.time_cost, params.parallelism) == (65536, 3, 4)
    assert (params.salt_len, params.hash_len) == (16, 32)
    different_salt_and_hash = second.secret_hash != issued.record.secret_hash
    assert different_salt_and_hash
    assert verify_credential(issued.value.to_wire(), second)


def test_record_contains_no_plaintext_or_device_identity(
    issued: IssuedCredential,
) -> None:
    assert {field.name for field in fields(CredentialRecord)} == {
        "key_id",
        "secret_hash",
        "created_at",
        "revoked_at",
        "replaced_at",
    }
    assert issued.record.created_at == NOW
    assert issued.record.state is CredentialState.ACTIVE
    with pytest.raises(FrozenInstanceError):
        issued.record.revoked_at = NOW  # type: ignore[misc]


def test_wire_round_trip_is_lossless(issued: IssuedCredential) -> None:
    parsed = CredentialValue.parse(issued.value.to_wire())
    assert parsed == issued.value


@pytest.mark.parametrize("length", (0, 31, 33))
def test_value_rejects_weak_or_wrong_length_secrets(length: int) -> None:
    with pytest.raises(CredentialError):
        CredentialValue(secrets.token_hex(16), secrets.token_bytes(length))


@pytest.mark.parametrize("candidate", (None, b"not-a-credential", 0))
def test_non_string_input_is_rejected(
    issued: IssuedCredential, candidate: object
) -> None:
    assert not verify_credential(cast(str, candidate), issued.record)


@pytest.mark.parametrize(
    "case",
    (
        "empty",
        "version",
        "bootstrap",
        "id_case",
        "short_id",
        "short_secret",
        "padding",
        "whitespace",
        "newline",
        "suffix",
        "noncanonical",
        "oversized",
    ),
)
def test_malformed_credentials_fail_closed_without_echo(
    issued: IssuedCredential,
    case: str,
) -> None:
    wire = issued.value.to_wire()
    secret = wire[40:]
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    variants = {
        "empty": "",
        "version": wire.replace("dwc_v1_", "dwc_v2_"),
        "bootstrap": wire.replace("dwc_v1_", "dwb_v1_"),
        "id_case": "dwc_v1_" + "A" * 32 + "_" + secret,
        "short_id": wire[:7] + wire[8:],
        "short_secret": wire[:-1],
        "padding": wire + "=",
        "whitespace": " " + wire,
        "newline": wire + "\n",
        "suffix": wire + "x",
        "noncanonical": wire[:-1] + alphabet[alphabet.index(wire[-1]) + 1],
        "oversized": wire + "x" * 10000,
    }
    candidate = variants[case]
    with pytest.raises(CredentialError) as error:
        CredentialValue.parse(candidate)
    assert str(error.value) == "Credential operation failed"
    assert not verify_credential(candidate, issued.record)


def test_wrong_secret_identifier_and_unknown_record_fail(
    issued: IssuedCredential,
) -> None:
    wrong_secret = CredentialValue(issued.value.key_id, secrets.token_bytes(32))
    wrong_id = CredentialValue(secrets.token_hex(16), issued.value.secret)
    assert not verify_credential(wrong_secret.to_wire(), issued.record)
    assert not verify_credential(wrong_id.to_wire(), issued.record)
    assert not verify_credential(issued.value.to_wire(), None)


@pytest.mark.parametrize(
    "replacement",
    (
        "",
        "malformed",
        "$argon2id$v=19$m=65536,t=3,p=4$",
        "x" * 10000,
    ),
)
def test_malformed_stored_hash_is_rejected(
    issued: IssuedCredential,
    replacement: str,
) -> None:
    damaged = replace(issued.record, secret_hash=replacement)
    assert not verify_credential(issued.value.to_wire(), damaged)


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("argon2id", "argon2i"),
        ("v=19", "v=16"),
        ("m=65536", "m=8"),
        ("m=65536", "m=999999999"),
        ("t=3", "t=1"),
        ("p=4", "p=1"),
    ),
)
def test_unsupported_hash_profiles_never_reach_native_verification(
    issued: IssuedCredential,
    old: str,
    new: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_verify(*args: object, **kwargs: object) -> bool:
        pytest.fail("Unsupported hash reached native verification")

    monkeypatch.setattr(type(credentials._HASHER), "verify", forbidden_verify)
    damaged = replace(
        issued.record, secret_hash=issued.record.secret_hash.replace(old, new)
    )
    assert not verify_credential(issued.value.to_wire(), damaged)


@pytest.mark.parametrize("field_index", (4, 5), ids=("salt", "digest"))
@pytest.mark.parametrize("corruption", ("pad_bits", "nul"))
def test_noncanonical_hash_never_reaches_native_verification(
    issued: IssuedCredential,
    field_index: int,
    corruption: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_verify(*args: object, **kwargs: object) -> bool:
        pytest.fail("Noncanonical hash reached native verification")

    monkeypatch.setattr(type(credentials._HASHER), "verify", forbidden_verify)
    parts = issued.record.secret_hash.split("$")
    if corruption == "pad_bits":
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        field = parts[field_index]
        parts[field_index] = field[:-1] + alphabet[alphabet.index(field[-1]) + 1]
    else:
        parts[field_index] = "\0" + parts[field_index][1:]
    damaged = replace(issued.record, secret_hash="$".join(parts))
    assert not verify_credential(issued.value.to_wire(), damaged)


def test_revocation_rejects_old_value_without_mutating_original(
    issued: IssuedCredential,
) -> None:
    revoked = revoke_credential(issued.record, revoked_at=NOW + timedelta(seconds=1))
    assert revoked.state is CredentialState.REVOKED
    assert revoked.revoked_at == NOW + timedelta(seconds=1)
    assert revoked.replaced_at is None
    assert not verify_credential(issued.value.to_wire(), revoked)
    assert issued.record.state is CredentialState.ACTIVE
    assert verify_credential(issued.value.to_wire(), issued.record)
    with pytest.raises(CredentialError):
        revoke_credential(revoked, revoked_at=NOW + timedelta(seconds=2))
    with pytest.raises(CredentialError):
        rotate_credential(revoked, clock=lambda: NOW + timedelta(seconds=2))


def test_rotation_returns_both_atomic_write_inputs(issued: IssuedCredential) -> None:
    rotated = rotate_credential(issued.record, clock=lambda: NOW + timedelta(seconds=2))
    assert rotated.previous.state is CredentialState.REPLACED
    assert rotated.previous.revoked_at == rotated.previous.replaced_at
    assert rotated.previous.revoked_at == NOW + timedelta(seconds=2)
    assert rotated.replacement.record.created_at == NOW + timedelta(seconds=2)
    assert rotated.replacement.record.key_id != rotated.previous.key_id
    assert not verify_credential(issued.value.to_wire(), rotated.previous)
    assert verify_credential(
        rotated.replacement.value.to_wire(), rotated.replacement.record
    )
    assert not verify_credential(issued.value.to_wire(), rotated.replacement.record)
    assert issued.record.state is CredentialState.ACTIVE
    with pytest.raises(CredentialError):
        rotate_credential(rotated.previous, clock=lambda: NOW + timedelta(seconds=3))


def test_lifecycle_rejects_naive_and_reversed_times(issued: IssuedCredential) -> None:
    for invalid in (NOW.replace(tzinfo=None), NOW - timedelta(seconds=1)):
        with pytest.raises(CredentialError):
            revoke_credential(issued.record, revoked_at=invalid)
    with pytest.raises(CredentialError):
        replace(issued.record, replaced_at=NOW)
    with pytest.raises(CredentialError):
        replace(issued.record, revoked_at=NOW, replaced_at=NOW + timedelta(seconds=1))
    offset = NOW.astimezone(timezone(timedelta(hours=5, minutes=30)))
    revoked = revoke_credential(issued.record, revoked_at=offset)
    assert revoked.revoked_at is not None and revoked.revoked_at.tzinfo is UTC


def test_representations_and_logs_hide_credentials_and_hashes(
    issued: IssuedCredential,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        logging.getLogger("credential-test").info(
            "value=%s issued=%r stored=%s", issued.value, issued, issued.record
        )
    output = caplog.text + repr(issued.value) + str(issued) + repr(issued.record)
    assert issued.value.to_wire() not in output
    assert issued.record.secret_hash not in output
    assert repr(issued.value.secret) not in output


def test_native_errors_are_sanitized_and_failed_rotation_has_no_side_effect(
    issued: IssuedCredential,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_hash(*args: object, **kwargs: object) -> str:
        raise HashingError(issued.value.to_wire() + issued.record.secret_hash)

    monkeypatch.setattr(type(credentials._HASHER), "hash", failed_hash)
    with pytest.raises(CredentialError) as failure:
        rotate_credential(issued.record, clock=lambda: NOW + timedelta(seconds=1))
    assert str(failure.value) == "Credential operation failed"
    assert failure.value.__suppress_context__
    assert issued.record.state is CredentialState.ACTIVE

    def failed_verify(*args: object, **kwargs: object) -> bool:
        raise VerificationError(issued.value.to_wire() + issued.record.secret_hash)

    monkeypatch.setattr(type(credentials._HASHER), "verify", failed_verify)
    assert not verify_credential(issued.value.to_wire(), issued.record)
