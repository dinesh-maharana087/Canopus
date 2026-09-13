"""Offline characterization of the credential-only Alembic extension."""

from __future__ import annotations

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command


def test_credential_schema_extends_bootstrap_head_without_plaintext(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://db/device_watch")
    config = Config("server/alembic.ini")
    scripts = ScriptDirectory.from_config(config)
    revision = scripts.get_revision("20260913_0004")
    assert revision is not None and revision.down_revision == "20260908_0003"
    command.upgrade(config, "20260908_0003:20260913_0004", sql=True)
    output = capsys.readouterr().out.lower()
    assert output.count("create table") == 1
    assert "create table device_credentials" in output
    assert "key_id varchar(32) not null" in output
    assert "secret_hash varchar(97) not null" in output
    assert "device_id varchar(36) not null" in output
    assert "primary key (key_id)" in output
    assert "foreign key(device_id) references devices (device_id)" in output
    assert "create index ix_device_credentials_device_id" in output
    assert "created_at datetime not null" in output
    for name in ("last_used_at", "revoked_at", "replaced_at"):
        assert f"{name} datetime" in output
    assert "engine=innodb" in output
    assert "unique (device_id)" not in output
    for excluded in (
        "bootstrap_secret",
        "credential_value",
        "heartbeat",
        "connectivity",
        "metrics",
    ):
        assert excluded not in output


def test_credential_downgrade_preserves_prerequisite_tables(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://db/device_watch")
    command.downgrade(
        Config("server/alembic.ini"), "20260913_0004:20260908_0003", sql=True
    )
    output = capsys.readouterr().out.lower()
    assert "drop table device_credentials" in output
    assert output.count("drop table") == 1
    assert "drop table devices" not in output
    assert "drop table enrollment_bootstraps" not in output
