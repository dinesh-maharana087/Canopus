from __future__ import annotations

from pathlib import Path


def test_development_smoke_profile_is_isolated_and_portless() -> None:
    compose_text = Path("deploy/compose.dev.yml").read_text(encoding="utf-8")
    env_text = Path("deploy/.env.dev.example").read_text(encoding="utf-8")

    assert "server-smoke:" in compose_text
    assert "profiles:" in compose_text
    assert "- verification" in compose_text
    assert "condition: service_healthy" in compose_text
    assert "DEVICE_WATCH_ENV: test" in compose_text
    assert "mysql+pymysql://device_watch_dev:device_watch_dev@mysql:3306/device_watch" in compose_text
    assert compose_text.count("server-smoke:") == 1
    assert "server-smoke:" in compose_text[compose_text.index("server-smoke:") :]
    smoke_section = compose_text[compose_text.index("server-smoke:") :]
    assert "ports:" not in smoke_section
    assert "caddy" not in compose_text.lower()
    assert "certificate" not in compose_text.lower()
    assert "device_watch_dev" in env_text
    assert "compose.prod" not in compose_text.lower()
