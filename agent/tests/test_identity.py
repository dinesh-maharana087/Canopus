"""Protected identity file behavior on the host filesystem, without HTTP."""

from __future__ import annotations

import base64
import importlib
import json
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from device_watch_agent.config import AgentSettingsError, load_settings
from device_watch_agent.identity import (
    AgentIdentity,
    IdentityError,
    IdentityState,
    IdentityStore,
)

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)
DEVICE = UUID("12345678-1234-4234-8234-123456789abc")


def require(condition: bool, message: str) -> None:
    if not condition:
        pytest.fail(message, pytrace=False)


def credential() -> str:
    # Synthetic test material only; the agent does not issue credentials.
    return (
        "dwc_v1_"
        + "1" * 32
        + "_"
        + base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
    )


def record() -> AgentIdentity:
    return AgentIdentity(device_id=DEVICE, credential=credential(), created_at=NOW)


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "private identity" / "identity.json"


def test_missing_storage_is_unenrolled_without_creating_files(path: Path) -> None:
    assert IdentityStore(path).load() is None
    assert not path.parent.exists()


def test_identity_survives_restart_and_file_has_only_approved_fields(
    path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    IdentityStore(path).save(record())
    restored = IdentityStore(path).load()
    require(restored == record(), "Restart did not restore the valid identity")
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(
        set(payload) == {"version", "device_id", "credential", "created_at"},
        "Unexpected file fields",
    )
    require(
        payload["version"] == 1 and payload["device_id"] == str(DEVICE),
        "Invalid file identity",
    )
    require(
        payload["credential"] == credential(), "File did not retain issued credential"
    )
    require(
        credential() not in repr(restored) + str(restored) + capsys.readouterr().out,
        "Default representation or logs exposed credentials",
    )
    assert sorted(item.name for item in path.parent.iterdir()) == ["identity.json"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", 2),
        ("version", True),
        ("version", 1.0),
        ("device_id", "12345678-1234-1234-8234-123456789abc"),
        ("device_id", "12345678-1234-4234-8234-123456789ABC"),
        ("credential", "wrong"),
        ("credential", "dwc_v1_" + "1" * 32 + "_" + "A" * 42 + "B"),
        ("created_at", "2026-09-14T12:00:00"),
        ("created_at", "invalid"),
        ("created_at", 42),
        ("unexpected", "private-extra-data"),
    ],
    ids=[
        "version",
        "boolean-version",
        "float-version",
        "non-v4",
        "noncanonical-uuid",
        "bad-credential",
        "noncanonical-credential",
        "naive-time",
        "bad-time",
        "numeric-time",
        "extra-field",
    ],
)
def test_malformed_record_fails_closed(path: Path, field: str, value: object) -> None:
    IdentityStore(path).save(record())
    payload = json.loads(path.read_text())
    payload[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(IdentityError, match="^Identity storage unavailable$"):
        IdentityStore(path).load()


@pytest.mark.parametrize(
    "raw",
    [b"", b"[]", b"null", b"{", b"\xff", b"x" * 4097, b'{"version":1,"version":1}'],
    ids=[
        "empty",
        "array",
        "null",
        "truncated",
        "encoding",
        "oversized",
        "duplicate-keys",
    ],
)
def test_invalid_file_encoding_shape_or_size_is_rejected(
    path: Path, raw: bytes
) -> None:
    IdentityStore(path).save(record())
    path.write_bytes(raw)
    with pytest.raises(IdentityError):
        IdentityStore(path).load()


def test_invalid_model_does_not_replace_valid_identity(path: Path) -> None:
    store = IdentityStore(path)
    store.save(record())
    with pytest.raises(IdentityError):
        AgentIdentity(
            device_id=DEVICE,
            credential=credential(),
            created_at=NOW.replace(tzinfo=None),
        )
    with pytest.raises(IdentityError):
        store.save(object())  # type: ignore[arg-type]
    require(store.load() == record(), "Invalid replacement destroyed valid identity")


def test_oversized_valid_json_cannot_bypass_limit_through_truncation(
    path: Path,
) -> None:
    store = IdentityStore(path)
    store.save(record())
    payload = path.read_bytes()
    path.write_bytes(payload + b" " * (4097 - len(payload)))
    with pytest.raises(IdentityError):
        store.load()


def test_failed_exclusive_temp_creation_does_not_delete_an_existing_file(
    path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = IdentityStore(path)
    store.save(record())
    collision = path.parent / (".identity-" + "a" * 32 + ".tmp")
    collision.write_bytes(b"preserve unrelated temporary file")
    monkeypatch.setattr(secrets, "token_hex", lambda size: "a" * 32)
    with pytest.raises(IdentityError):
        store.save(record())
    assert collision.read_bytes() == b"preserve unrelated temporary file"
    require(store.load() == record(), "Exclusive create failure changed identity")


def test_aware_timestamp_is_normalized_to_utc() -> None:
    offset = NOW.astimezone(timezone(timedelta(hours=5, minutes=30)))
    value = AgentIdentity(device_id=DEVICE, credential=credential(), created_at=offset)
    assert value.created_at == NOW and value.created_at.tzinfo is UTC


@pytest.mark.parametrize(
    "timestamp", ["0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"]
)
def test_timestamp_outside_utc_range_has_sanitized_error(
    path: Path, timestamp: str
) -> None:
    store = IdentityStore(path)
    store.save(record())
    payload = json.loads(path.read_text())
    payload["created_at"] = timestamp
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(IdentityError, match="^Identity storage unavailable$"):
        store.load()


@pytest.mark.parametrize("operation", ["replace", "fsync"])
def test_interrupted_write_preserves_previous_file_and_cleans_temp(
    path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    store = IdentityStore(path)
    store.save(record())

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError(credential())

    with monkeypatch.context() as patch:
        if operation == "replace":
            module = importlib.import_module(
                "device_watch_agent._identity_windows"
                if os.name == "nt"
                else "device_watch_agent._identity_posix"
            )
            adapter = (
                module.WindowsDirectory if os.name == "nt" else module.PosixDirectory
            )
            patch.setattr(adapter, "replace", fail)
        else:
            patch.setattr(os, "fsync", fail)
        with pytest.raises(IdentityError) as error:
            store.save(
                AgentIdentity(
                    device_id=DEVICE,
                    credential=credential(),
                    created_at=NOW + timedelta(days=1),
                )
            )
        require(
            str(error.value) == "Identity storage unavailable"
            and error.value.__suppress_context__,
            "Write failure exposed internal diagnostics",
        )
    require(
        IdentityStore(path).load() == record(),
        "Interrupted write lost previous valid identity",
    )
    assert sorted(item.name for item in path.parent.iterdir()) == ["identity.json"]


def test_invalidation_deletes_without_backup_and_returns_reenrollment_state(
    path: Path,
) -> None:
    store = IdentityStore(path)
    store.save(record())
    assert store.invalidate() is IdentityState.REENROLLMENT_REQUIRED
    assert IdentityStore(path).load() is None
    assert list(path.parent.iterdir()) == []
    assert store.invalidate() is IdentityState.REENROLLMENT_REQUIRED


def test_hard_link_is_rejected_before_read_replace_or_delete(path: Path) -> None:
    store = IdentityStore(path)
    store.save(record())
    alias = path.parent / "alias"
    os.link(path, alias)
    try:
        for operation in (store.load, lambda: store.save(record()), store.invalidate):
            with pytest.raises(IdentityError):
                operation()
    finally:
        alias.unlink()
    require(store.load() == record(), "Rejected hard link operation changed valid file")


def test_path_configuration_has_no_connection_or_secret_defaults(
    tmp_path: Path,
) -> None:
    default = load_settings({"DEVICE_WATCH_AGENT_MODE": "service"})
    assert default.identity_path.is_absolute()
    target = tmp_path / "storage with spaces" / "identity.json"
    configured = load_settings(
        {
            "DEVICE_WATCH_AGENT_MODE": "service",
            "DEVICE_WATCH_AGENT_IDENTITY_PATH": str(target),
        }
    )
    assert configured.identity_path == target
    for invalid in ("", "relative.json", str(tmp_path / ".." / "identity.json")):
        with pytest.raises(AgentSettingsError):
            load_settings(
                {
                    "DEVICE_WATCH_AGENT_MODE": "service",
                    "DEVICE_WATCH_AGENT_IDENTITY_PATH": invalid,
                }
            )


def test_posix_restrictive_modes_and_unsafe_permissions(path: Path) -> None:
    if sys.platform == "win32":
        pytest.skip("Requires POSIX ownership and permissions")
    store = IdentityStore(path)
    store.save(record())
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert path.stat().st_uid == os.geteuid()
    path.chmod(0o644)
    with pytest.raises(IdentityError):
        store.load()
    path.chmod(0o600)
    path.parent.chmod(0o750)
    with pytest.raises(IdentityError):
        store.load()


def test_posix_symlink_and_fifo_are_rejected(path: Path, tmp_path: Path) -> None:
    if sys.platform == "win32":
        pytest.skip("Requires POSIX symlinks and FIFO support")
    store = IdentityStore(path)
    store.save(record())
    path.unlink()
    target = tmp_path / "unrelated"
    target.write_text("keep", encoding="utf-8")
    path.symlink_to(target)
    with pytest.raises(IdentityError):
        store.load()
    assert target.read_text() == "keep"
    path.unlink()
    os.mkfifo(path, 0o600)
    with pytest.raises(IdentityError):
        store.load()
