"""Local operator bootstrap provisioning; plaintext is displayed once after commit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import NoReturn
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from device_watch_server.core.config import load_settings
from device_watch_server.db.engine import create_database_engine
from device_watch_server.enrollment.service import (
    DEFAULT_BOOTSTRAP_EXPIRY_MINUTES,
    GENERIC_BOOTSTRAP_FAILURE,
    BootstrapServiceError,
    provision_bootstrap,
    revoke_bootstrap,
)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse's default diagnostics echo arbitrary rejected arguments.
        raise BootstrapServiceError()


def main(argv: Sequence[str] | None = None) -> int:
    """Use protected server configuration and a trusted terminal, never secret args."""
    parser = _SafeParser(
        description="Provision or revoke one-time enrollment bootstraps locally.",
        allow_abbrev=False,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", allow_abbrev=False)
    create.add_argument(
        "--expires-in-minutes", type=int, default=DEFAULT_BOOTSTRAP_EXPIRY_MINUTES
    )
    create.add_argument("--label")
    revoke = commands.add_parser("revoke", allow_abbrev=False)
    revoke.add_argument("bootstrap_id", type=UUID)

    try:
        args = parser.parse_args(argv)
        if args.command == "create" and not sys.stdout.isatty():
            raise BootstrapServiceError()
        settings = load_settings()
        configured_pepper = settings.device_watch_bootstrap_hmac_pepper
        if args.command == "create" and configured_pepper is None:
            raise BootstrapServiceError()
        engine = create_database_engine(settings)
        try:
            with engine.begin() as connection:
                if args.command == "create":
                    issued = provision_bootstrap(
                        connection,
                        None
                        if configured_pepper is None
                        else configured_pepper.get_secret_value(),
                        expires_in_minutes=args.expires_in_minutes,
                        operator_label=args.label,
                    )
                else:
                    revoke_bootstrap(connection, args.bootstrap_id)
        finally:
            engine.dispose()

        if args.command == "create":
            print(
                "Bootstrap created\n"
                f"Bootstrap ID: {issued.bootstrap_id}\n"
                f"Expires at: {issued.expires_at.isoformat()}\n"
                "Copy the secret now; it cannot be displayed again.\n"
                "Use a protected terminal without recording. Keep secrets out of "
                "command arguments, URLs, logs, and shell history.\n"
                f"Bootstrap secret: {issued.bootstrap_value.to_wire()}",
                flush=True,
            )
        else:
            print(f"Bootstrap revoked\nBootstrap ID: {args.bootstrap_id}")
    except (OSError, RuntimeError, ValueError, SQLAlchemyError):
        # Driver/config/parser failures may carry secrets; never format or log them.
        print(GENERIC_BOOTSTRAP_FAILURE, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
