"""Command-line checks for the Device Watch database readiness."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from device_watch_server.core.config import SettingsError, load_settings
from device_watch_server.core.logging import setup_logging
from device_watch_server.db.engine import create_database_engine
from device_watch_server.db.health import check_database

logger = logging.getLogger("device_watch_server.cli")


def main(argv: Sequence[str] | None = None) -> int:
    """Run a one-shot database connectivity check and return the shell status code."""

    parser = argparse.ArgumentParser(description="Check database connectivity for Device Watch")
    parser.parse_args(argv)
    setup_logging()

    try:
        settings = load_settings()
        engine = create_database_engine(settings)
        try:
            check_database(engine)
        finally:
            engine.dispose()
    except (SettingsError, RuntimeError, OSError, ValueError):
        print("database connectivity: unavailable", file=sys.stderr)
        return 1

    print("database connectivity: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
