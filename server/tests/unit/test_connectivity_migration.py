"""Step 10 MySQL DDL and directly affected device metadata contracts."""

from __future__ import annotations

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from alembic import command
from device_watch_server.db.connectivity import device_connectivity_table
from device_watch_server.enrollment.persistence import devices_table

REVISION = "20260914_0005"
PREVIOUS = "20260913_0004"
IDENTITY = "20260908_0002"
STATE_COLUMNS = {
    "last_seen_at",
    "last_heartbeat_submission_id",
    "last_agent_version",
}


@pytest.fixture
def migration_config(monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://db/device_watch")
    return Config("server/alembic.ini")


def test_connectivity_extends_existing_head_without_forking(
    migration_config: Config,
) -> None:
    scripts = ScriptDirectory.from_config(migration_config)
    assert scripts.get_heads() == [REVISION]
    revision = scripts.get_revision(REVISION)
    assert revision is not None and revision.down_revision == PREVIOUS
    assert [item.revision for item in scripts.iterate_revisions(REVISION, IDENTITY)] == [
        REVISION,
        PREVIOUS,
        "20260908_0003",
    ]


def test_upgrade_adds_only_nullable_current_state_and_its_constraints(
    migration_config: Config, capsys: pytest.CaptureFixture[str]
) -> None:
    command.upgrade(migration_config, f"{PREVIOUS}:{REVISION}", sql=True)
    ddl = capsys.readouterr().out.lower()
    assert "add column last_seen_at datetime(6)" in ddl
    assert "add column last_heartbeat_submission_id varchar(36)" in ddl
    assert "add column last_agent_version varchar(64)" in ddl
    assert ddl.count("add column") == 3
    assert "check (last_heartbeat_submission_id is null or last_seen_at is not null)" in ddl
    assert "create index ix_devices_last_seen_at on devices (last_seen_at)" in ddl
    for forbidden in (
        "create table",
        "drop table",
        "not null;",
        "default",
        "on update",
        "unique",
        "foreign key",
        "credential",
        "observed_at",
        "metrics",
        "history",
        "body",
    ):
        assert forbidden not in ddl


def test_downgrade_removes_only_current_state_and_preserves_prior_head(
    migration_config: Config, capsys: pytest.CaptureFixture[str]
) -> None:
    command.downgrade(migration_config, f"{REVISION}:{PREVIOUS}", sql=True)
    ddl = capsys.readouterr().out.lower()
    assert "drop index ix_devices_last_seen_at on devices" in ddl
    assert "drop check ck_devices_submission_requires_last_seen" in ddl
    for name in STATE_COLUMNS:
        assert f"drop column {name}" in ddl
    assert ddl.count("drop column") == 3
    assert "drop table" not in ddl
    assert ddl.index("drop check") < ddl.index("drop column")
    assert PREVIOUS in ddl


def test_step02_upgrade_and_downgrade_paths_preserve_device_identity(
    migration_config: Config, capsys: pytest.CaptureFixture[str]
) -> None:
    command.upgrade(migration_config, f"{IDENTITY}:{REVISION}", sql=True)
    upgrade = capsys.readouterr().out.lower()
    assert "create table devices" not in upgrade
    assert "alter table devices add column last_seen_at datetime(6)" in upgrade
    assert upgrade.count("create table") == 2  # Existing 0003/0004 prerequisites.
    command.downgrade(migration_config, f"{REVISION}:{IDENTITY}", sql=True)
    downgrade = capsys.readouterr().out.lower()
    assert "drop table devices" not in downgrade
    assert downgrade.count("drop table") == 2
    assert downgrade.count("drop column") == 3


def test_device_metadata_matches_current_state_ddl_without_history() -> None:
    state_table = device_connectivity_table
    assert state_table.name == "devices"
    assert set(state_table.c.keys()) == STATE_COLUMNS | {"device_id"}
    for name in STATE_COLUMNS:
        column = state_table.c[name]
        assert column.nullable
        assert column.default is None and column.server_default is None
        assert column.onupdate is None and column.server_onupdate is None
    assert list(state_table.primary_key.columns.keys()) == ["device_id"]
    assert not state_table.c.last_heartbeat_submission_id.unique
    assert {
        (index.name, tuple(index.columns.keys()), index.unique)
        for index in state_table.indexes
    } == {("ix_devices_last_seen_at", ("last_seen_at",), False)}
    ddl = str(CreateTable(state_table).compile(dialect=mysql.dialect())).lower()
    assert "last_seen_at datetime(6)" in ddl
    assert "last_heartbeat_submission_id varchar(36)" in ddl
    assert "last_agent_version varchar(64)" in ddl
    assert "check (last_heartbeat_submission_id is null or last_seen_at is not null)" in ddl


def test_connectivity_projection_preserves_enrollment_identity_queries() -> None:
    identity_sql = str(select(devices_table).compile(dialect=mysql.dialect()))
    state_sql = str(select(device_connectivity_table).compile(dialect=mysql.dialect()))
    for name in STATE_COLUMNS:
        assert name not in identity_sql
        assert name in state_sql
    assert "devices.device_id" in state_sql
    assert "FROM devices" in state_sql
