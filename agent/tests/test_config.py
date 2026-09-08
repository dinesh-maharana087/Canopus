from __future__ import annotations

import pytest

from device_watch_agent.config import AgentSettingsError, load_settings


def test_missing_mode_fails() -> None:
    with pytest.raises(AgentSettingsError, match="MODE is required"):
        load_settings({})


@pytest.mark.parametrize("mode", ["", "development", "test", "service "])
def test_only_service_mode_is_supported(mode: str) -> None:
    with pytest.raises(AgentSettingsError, match="must be 'service'"):
        load_settings({"DEVICE_WATCH_AGENT_MODE": mode})


def test_default_and_positive_interval() -> None:
    assert load_settings({"DEVICE_WATCH_AGENT_MODE": "service"}).interval_seconds == 30.0
    assert load_settings(
        {
            "DEVICE_WATCH_AGENT_MODE": "service",
            "DEVICE_WATCH_AGENT_INTERVAL_SECONDS": "2.5",
        }
    ).interval_seconds == 2.5


@pytest.mark.parametrize("interval", ["0", "-1", "not-a-number"])
def test_non_positive_or_invalid_interval_fails(interval: str) -> None:
    with pytest.raises(AgentSettingsError, match="positive number"):
        load_settings(
            {
                "DEVICE_WATCH_AGENT_MODE": "service",
                "DEVICE_WATCH_AGENT_INTERVAL_SECONDS": interval,
            }
        )


def test_unknown_agent_settings_fail_without_server_settings() -> None:
    with pytest.raises(AgentSettingsError, match="Unknown agent setting"):
        load_settings(
            {
                "DEVICE_WATCH_AGENT_MODE": "service",
                "DEVICE_WATCH_AGENT_SECRET": "unexpected",
            }
        )
