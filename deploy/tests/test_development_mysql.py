from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPOSITORY_ROOT / "deploy" / "compose.dev.yml"
ENV_FILE = REPOSITORY_ROOT / "deploy" / ".env.dev.example"
DEVELOPMENT_MYSQL_VARIABLES = frozenset(
    {
        "MYSQL_ROOT_PASSWORD",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
    }
)


def _render_development_compose() -> dict[str, Any]:
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker is unavailable; Compose rendering is environment-blocked")

    environment = os.environ.copy()
    for name in DEVELOPMENT_MYSQL_VARIABLES:
        environment.pop(name, None)

    result = subprocess.run(
        [
            docker,
            "compose",
            "--env-file",
            str(ENV_FILE),
            "-f",
            str(COMPOSE_FILE),
            "config",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    return cast(dict[str, Any], json.loads(result.stdout))


def test_development_compose_render_ignores_host_mysql_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded_mysql_names: set[str] = set()

    for name in DEVELOPMENT_MYSQL_VARIABLES:
        monkeypatch.setenv(name, "harmless-host-override")
    monkeypatch.setattr(shutil, "which", lambda executable: executable)

    def capture_subprocess_environment(
        args: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        effective_environment = os.environ if env is None else env
        forwarded_mysql_names.update(
            DEVELOPMENT_MYSQL_VARIABLES.intersection(effective_environment)
        )
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", capture_subprocess_environment)

    assert _render_development_compose() == {}
    assert forwarded_mysql_names == set()


def test_development_mysql_topology_is_rendered_from_dev_env_only() -> None:
    assert COMPOSE_FILE.is_file(), "deploy/compose.dev.yml is required for Step 04"
    assert ENV_FILE.is_file(), "deploy/.env.dev.example is required for Step 04"

    rendered = _render_development_compose()
    services = cast(dict[str, Any], rendered["services"])
    mysql = cast(dict[str, Any], services["mysql"])

    assert mysql["image"] == "mysql:8.4.11"
    assert mysql["environment"] == {
        "MYSQL_DATABASE": "device_watch",
        "MYSQL_PASSWORD": "device_watch_dev",
        "MYSQL_ROOT_PASSWORD": "root_dev_password",
        "MYSQL_USER": "device_watch_dev",
    }

    ports = cast(list[dict[str, Any]], mysql["ports"])
    assert len(ports) == 1
    assert ports[0]["host_ip"] == "127.0.0.1"
    assert str(ports[0]["published"]) == "3307"
    assert ports[0]["target"] == 3306
    assert ports[0]["protocol"] == "tcp"

    volumes = cast(list[dict[str, Any]], mysql["volumes"])
    assert len(volumes) == 1
    assert volumes[0]["type"] == "volume"
    assert volumes[0]["source"] == "mysql_dev_data"
    assert volumes[0]["target"] == "/var/lib/mysql"
    assert cast(dict[str, Any], rendered["volumes"])["mysql_dev_data"][
        "name"
    ] == "mysql_dev_data"

    healthcheck = cast(dict[str, Any], mysql["healthcheck"])
    assert healthcheck["test"] == [
        "CMD",
        "mysqladmin",
        "ping",
        "-h",
        "127.0.0.1",
        "-u",
        "root",
        "--password=root_dev_password",
    ]
    assert healthcheck["interval"] == "10s"
    assert healthcheck["timeout"] == "5s"
    assert healthcheck["retries"] == 10
    assert healthcheck["start_period"] == "15s"

    assert "caddy" not in services
    assert "server" not in services
