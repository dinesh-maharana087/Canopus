from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from device_watch_server.db.base import Base


def test_bootstrap_revision_creates_secret_safe_enrollment_storage(
    monkeypatch, capsys
) -> None:
    """Catch a migration that omits or weakens bootstrap persistence constraints."""
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://migration_user:migration_password@db/device_watch",
    )

    config = Config("server/alembic.ini")
    config.set_main_option("script_location", str(Path("server/alembic").resolve()))
    scripts = ScriptDirectory.from_config(config)
    revision = scripts.get_revision("20260908_0003")

    assert revision is not None
    assert revision.down_revision == "20260908_0002"
    assert Base.metadata.tables == {}

    command.upgrade(config, "20260908_0003", sql=True)
    output = capsys.readouterr().out.lower()
    bootstrap_sql = output.split("create table enrollment_bootstraps", maxsplit=1)[1]

    assert "create table enrollment_bootstraps" in output
    assert "bootstrap_id varchar(36) not null" in output
    assert "lookup_fingerprint binary(32) not null" in output
    assert "digest_version varchar(32) not null" in output
    assert "digest binary(32) not null" in output
    assert "operator_label varchar(120)" in output
    assert "created_at datetime not null" in output
    assert "expires_at datetime not null" in output
    assert "consumed_at datetime" in output
    assert "revoked_at datetime" in output
    assert "uq_enrollment_bootstraps_lookup_fingerprint" in output
    assert "ck_enrollment_bootstraps_expires_after_created" in output
    assert "ck_enrollment_bootstraps_terminal_exclusive" in output
    assert "ck_enrollment_bootstraps_consumed_not_before_created" in output
    assert "ck_enrollment_bootstraps_revoked_not_before_created" in output
    assert "bootstrap_value" not in bootstrap_sql
    assert "device_id" not in bootstrap_sql
    assert "credential" not in bootstrap_sql
    assert "lifecycle" not in bootstrap_sql


def test_bootstrap_downgrade_removes_only_bootstrap_storage(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://db/device_watch")
    config = Config("server/alembic.ini")

    command.downgrade(config, "20260908_0003:20260908_0002", sql=True)

    output = capsys.readouterr().out.lower()
    assert "drop table enrollment_bootstraps" in output
    assert "drop table devices" not in output
    assert output.count("drop table") == 1
    assert "20260908_0002" in output
