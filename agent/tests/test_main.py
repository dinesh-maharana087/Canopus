"""Tests for native agent process wiring."""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Callable
from typing import cast

from device_watch_agent.main import _install_signal_handlers


class SignalCapturingLoop:
    def __init__(self) -> None:
        self.handlers: dict[signal.Signals, Callable[[], None]] = {}

    def add_signal_handler(
        self,
        signum: signal.Signals,
        callback: Callable[[], None],
        *args: object,
    ) -> None:
        assert args == ()
        self.handlers[signum] = callback


def test_supported_loop_installs_sigint_and_sigterm_stop_callbacks() -> None:
    stop_event = asyncio.Event()
    capturing_loop = SignalCapturingLoop()

    _install_signal_handlers(
        stop_event,
        cast(asyncio.AbstractEventLoop, capturing_loop),
    )

    assert set(capturing_loop.handlers) == {signal.SIGINT, signal.SIGTERM}
    for callback in capturing_loop.handlers.values():
        callback()
        assert stop_event.is_set()
        stop_event.clear()
