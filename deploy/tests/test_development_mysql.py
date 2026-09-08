from __future__ import annotations

from pathlib import Path


def test_development_mysql_topology_is_rendered_from_dev_env_only() -> None:
    compose_file = Path("deploy/compose.dev.yml")
    env_file = Path("deploy/.env.dev.example")

    assert compose_file.exists(), "deploy/compose.dev.yml is required for Step 04"
    assert env_file.exists(), "deploy/.env.dev.example is required for Step 04"

    raw = compose_file.read_text(encoding="utf-8")
    assert "mysql:8.4.11" in raw
    assert "127.0.0.1:3307:3306" in raw
    assert "mysql_dev_data" in raw
    assert "healthcheck" in raw.lower()
    assert "MYSQL_ROOT_PASSWORD" in raw
    assert "MYSQL_DATABASE" in raw
    assert "MYSQL_USER" in raw
    assert "MYSQL_PASSWORD" in raw

    env_text = env_file.read_text(encoding="utf-8")
    assert "MYSQL_ROOT_PASSWORD" in env_text
    assert "MYSQL_DATABASE" in env_text
    assert "MYSQL_USER" in env_text
    assert "MYSQL_PASSWORD" in env_text
    assert "MYSQL_ROOT_PASSWORD=root_dev_password" in env_text
    assert "MYSQL_DATABASE=device_watch" in env_text
    assert "MYSQL_USER=device_watch_dev" in env_text
    assert "MYSQL_PASSWORD=device_watch_dev" in env_text

    assert "production" not in raw.lower()
    assert "compose.prod" not in raw.lower()
