"""Focused regression coverage for the Stage 1 Alembic boundary."""

from __future__ import annotations

import io
from pathlib import Path
from typing import NoReturn

import pymysql  # type: ignore[import-untyped]
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

from alembic import command
from device_watch_server.db.base import Base

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG = REPOSITORY_ROOT / "server" / "alembic.ini"
ALEMBIC_SCRIPTS = REPOSITORY_ROOT / "server" / "alembic"
BASELINE_REVISION = "20260831_0001"


def test_metadata_generates_deterministic_constraint_names() -> None:
    """A missing convention must not leave future constraints unnamed."""

    metadata = MetaData(naming_convention=Base.metadata.naming_convention)
    parent = Table(
        "parent",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("serial", String(32), unique=True),
    )
    positive_id = CheckConstraint(parent.c.id > 0)
    parent.append_constraint(positive_id)
    serial_index = Index(None, parent.c.serial)
    child = Table(
        "child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey("parent.id"), nullable=False),
    )

    unique_serial = next(
        constraint
        for constraint in parent.constraints
        if isinstance(constraint, UniqueConstraint)
    )
    parent_reference = next(iter(child.foreign_key_constraints))

    assert parent.primary_key.name == "pk_parent"
    assert unique_serial.name == "uq_parent_serial"
    assert positive_id.name == "ck_parent_id"
    assert parent_reference.name == "fk_child_parent_id_parent"
    assert serial_index.name == "ix_parent_serial"
    assert Base.metadata.tables == {}


def test_script_location_resolves_relative_to_alembic_ini() -> None:
    """Repository-root Alembic commands must locate the server scripts."""

    scripts = ScriptDirectory.from_config(Config(str(ALEMBIC_CONFIG)))

    assert Path(scripts.dir).resolve() == ALEMBIC_SCRIPTS.resolve()


def test_offline_migration_accepts_percent_containing_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A percent-encoded credential must bypass ConfigParser interpolation."""

    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://device:p%25ss@example.invalid/device_watch",
    )
    output = io.StringIO()
    config = Config(str(ALEMBIC_CONFIG), output_buffer=output)

    command.upgrade(config, BASELINE_REVISION, sql=True)

    migration_sql = output.getvalue()
    assert "alembic_version" in migration_sql
    assert BASELINE_REVISION in migration_sql
    assert "p%25ss" not in migration_sql


def test_online_migration_preserves_validated_pymysql_tls_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Alembic must reach PyMySQL with booleans and no competing SSL map."""

    class StopBeforeNetwork(Exception):
        pass

    captured: dict[str, object] = {}

    def capture_connect(*args: object, **kwargs: object) -> NoReturn:
        captured.update(kwargs)
        raise StopBeforeNetwork

    monkeypatch.setattr(pymysql, "connect", capture_connect)
    monkeypatch.setenv("DEVICE_WATCH_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://device:synthetic@example.invalid/device_watch"
        "?ssl_ca=/run/secrets/mysql-ca.pem"
        "&ssl_verify_cert=true"
        "&ssl_verify_identity=true",
    )

    with pytest.raises(StopBeforeNetwork):
        command.upgrade(Config(str(ALEMBIC_CONFIG)), BASELINE_REVISION)

    tls_arguments = {
        key: captured[key]
        for key in ("ssl_ca", "ssl_verify_cert", "ssl_verify_identity")
        if key in captured
    }
    assert tls_arguments == {
        "ssl_ca": "/run/secrets/mysql-ca.pem",
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    }
    assert "ssl" not in captured
