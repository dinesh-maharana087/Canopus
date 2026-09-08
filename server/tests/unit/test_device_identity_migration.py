from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command


def test_device_identity_revision_chain_and_offline_sql(
    monkeypatch, capsys
) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://migration_user:migration_password@db/device_watch",
    )

    config = Config("server/alembic.ini")
    config.set_main_option("script_location", str(Path("server/alembic").resolve()))
    scripts = ScriptDirectory.from_config(config)
    revision = scripts.get_revision("20260908_0002")
    assert revision is not None
    assert revision.down_revision == "20260831_0001"

    command.upgrade(config, "20260908_0002", sql=True)
    output = capsys.readouterr().out.lower()

    assert "create table devices" in output
    assert "device_id varchar(36) not null" in output
    assert "display_name varchar(120) not null" in output
    assert "created_at datetime not null" in output
    assert "lifecycle varchar(16)" in output
    assert "primary key (device_id)" in output
    assert "ck_devices_lifecycle" in output
    assert "credential" not in output
    assert "bootstrap" not in output
    assert "heartbeat" not in output
