from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def clear_server_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "DEVICE_WATCH_ENV",
        "DATABASE_URL",
        "DEVICE_WATCH_ENABLE_DOCS",
        "DEVICE_WATCH_BOOTSTRAP_HMAC_PEPPER",
    ):
        monkeypatch.delenv(name, raising=False)
