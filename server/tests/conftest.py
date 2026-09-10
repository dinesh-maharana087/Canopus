from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def clear_server_environment(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    names: tuple[str, ...] = (
        "DEVICE_WATCH_ENABLE_DOCS",
        "DEVICE_WATCH_BOOTSTRAP_HMAC_PEPPER",
    )
    if request.node.get_closest_marker("integration") is None:
        names += ("DEVICE_WATCH_ENV", "DATABASE_URL")

    for name in names:
        monkeypatch.delenv(name, raising=False)
