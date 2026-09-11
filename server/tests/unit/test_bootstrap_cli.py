from __future__ import annotations

import builtins
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock
from uuid import UUID

import pytest
from pydantic import SecretStr
from sqlalchemy.engine import Connection

from device_watch_server.core.config import SettingsError
from device_watch_server.enrollment import cli as bootstrap_cli
from device_watch_server.enrollment import service
from device_watch_server.enrollment.bootstrap import BootstrapValue
from device_watch_server.enrollment.repository import BootstrapRecord
from device_watch_server.enrollment.service import (
    BootstrapServiceError,
    ProvisionedBootstrap,
)

HMAC_PEPPER = "bootstrap-cli-pepper-material-32-bytes-minimum"
NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
FIXED_WIRE_VALUE = "dwb_v1_AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE"
FIXED_BOOTSTRAP_ID = UUID("c919f0d6-17a7-4b4c-b579-e1cc4ce2bb03")


def _settings(configured_pepper: str | None = HMAC_PEPPER) -> SimpleNamespace:
    pepper_value = (
        None if configured_pepper is None else SecretStr(configured_pepper)
    )
    return SimpleNamespace(device_watch_bootstrap_hmac_pepper=pepper_value)


class _TransactionEngine:
    """Record the CLI's transaction boundary without opening a database."""

    def __init__(self) -> None:
        self.connection = cast(Connection, Mock(spec_set=Connection))
        self.events: list[str] = []
        self.transaction_active = False
        self.disposed = False

    @contextmanager
    def begin(self) -> Iterator[Connection]:
        self.transaction_active = True
        try:
            yield self.connection
        except Exception:
            self.events.append("rollback")
            raise
        else:
            self.events.append("commit")
        finally:
            self.transaction_active = False

    def dispose(self) -> None:
        self.disposed = True


def _assert_generic_failure(
    capsys: pytest.CaptureFixture[str],
    *sensitive_values: str,
) -> None:
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Bootstrap operation failed\n"
    for sensitive_value in sensitive_values:
        assert sensitive_value not in captured.err


def test_create_prints_plaintext_once_only_after_commit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = _TransactionEngine()
    inserted: list[BootstrapRecord] = []

    def capture_insert(connection: Connection, record: BootstrapRecord) -> None:
        assert connection is engine.connection
        assert engine.transaction_active
        inserted.append(record)

    monkeypatch.setattr(service, "insert_bootstrap", capture_insert)
    monkeypatch.setattr(bootstrap_cli, "load_settings", _settings)
    monkeypatch.setattr(
        bootstrap_cli,
        "create_database_engine",
        lambda settings: engine,
    )
    events = engine.events
    real_print = builtins.print

    def recording_print(*args: object, **kwargs: object) -> None:
        events.append("print")
        real_print(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "print", recording_print)

    exit_code = bootstrap_cli.main(
        ["create", "--expires-in-minutes", "7", "--label", "  night shift  "]
    )

    captured = capsys.readouterr()
    wire_values = re.findall(r"dwb_v1_[A-Za-z0-9_-]{43}", captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert len(wire_values) == 1
    assert events[0] == "commit"
    assert events.index("commit") < events.index("print")
    assert "Bootstrap created" in captured.out
    assert "Bootstrap ID:" in captured.out
    assert "Expires at:" in captured.out
    assert "command arguments" in captured.out
    assert "URLs" in captured.out
    assert "shell history" in captured.out
    assert HMAC_PEPPER not in captured.out
    assert engine.disposed
    assert len(inserted) == 1
    assert inserted[0].operator_label == "night shift"
    assert inserted[0].expires_at - inserted[0].created_at == timedelta(minutes=7)


class _FailingCommit:
    def __enter__(self) -> object:
        return object()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        raise RuntimeError(
            f"commit failed {FIXED_WIRE_VALUE} {HMAC_PEPPER} database-private-value"
        )


class _CommitFailingEngine:
    def begin(self) -> _FailingCommit:
        return _FailingCommit()

    def dispose(self) -> None:
        return None


def test_create_does_not_print_plaintext_when_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pending_result = ProvisionedBootstrap(
        bootstrap_id=FIXED_BOOTSTRAP_ID,
        bootstrap_value=BootstrapValue.parse(FIXED_WIRE_VALUE),
        operator_label=None,
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )
    monkeypatch.setattr(bootstrap_cli, "load_settings", _settings)
    monkeypatch.setattr(
        bootstrap_cli,
        "create_database_engine",
        lambda settings: _CommitFailingEngine(),
    )
    monkeypatch.setattr(
        bootstrap_cli,
        "provision_bootstrap",
        lambda *args, **kwargs: pending_result,
    )

    assert bootstrap_cli.main(["create"]) == 1

    _assert_generic_failure(
        capsys,
        FIXED_WIRE_VALUE,
        HMAC_PEPPER,
        "database-private-value",
    )


@pytest.mark.parametrize(
    ("argv", "rejected_value"),
    (
        (["create", "--expires-in-minutes", "minutes-private-value"], "minutes-private-value"),
        (["create", "--pepper", "argument-private-value"], "argument-private-value"),
        (["revoke", "uuid-private-value"], "uuid-private-value"),
    ),
)
def test_argument_failures_are_generic_and_do_not_echo_rejected_values(
    argv: list[str],
    rejected_value: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert bootstrap_cli.main(argv) == 1

    _assert_generic_failure(capsys, rejected_value)


@pytest.mark.parametrize("failure_stage", ("configuration", "database"))
def test_configuration_and_database_failures_are_generic(
    failure_stage: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sensitive_detail = f"{failure_stage}-private-value"
    if failure_stage == "configuration":
        monkeypatch.setattr(
            bootstrap_cli,
            "load_settings",
            lambda: (_ for _ in ()).throw(SettingsError(sensitive_detail)),
        )
    else:
        monkeypatch.setattr(bootstrap_cli, "load_settings", _settings)
        monkeypatch.setattr(
            bootstrap_cli,
            "create_database_engine",
            lambda settings: (_ for _ in ()).throw(RuntimeError(sensitive_detail)),
        )

    assert bootstrap_cli.main(["create"]) == 1

    _assert_generic_failure(capsys, sensitive_detail)


def test_revoke_dispatches_the_id_and_commits_before_reporting_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = _TransactionEngine()

    def revoke_in_transaction(connection: Connection, bootstrap_id: UUID) -> UUID:
        assert connection is engine.connection
        assert engine.transaction_active
        return bootstrap_id

    revoke = Mock(side_effect=revoke_in_transaction)
    monkeypatch.setattr(bootstrap_cli, "revoke_bootstrap", revoke)
    monkeypatch.setattr(bootstrap_cli, "load_settings", lambda: _settings(None))
    monkeypatch.setattr(
        bootstrap_cli,
        "create_database_engine",
        lambda settings: engine,
    )

    real_print = builtins.print

    def recording_print(*args: object, **kwargs: object) -> None:
        engine.events.append("print")
        real_print(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "print", recording_print)

    exit_code = bootstrap_cli.main(["revoke", str(FIXED_BOOTSTRAP_ID)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        f"Bootstrap revoked\nBootstrap ID: {FIXED_BOOTSTRAP_ID}\n"
    )
    revoke.assert_called_once_with(engine.connection, FIXED_BOOTSTRAP_ID)
    assert engine.events[0] == "commit"
    assert engine.events.index("commit") < engine.events.index("print")
    assert engine.disposed


def test_unknown_revoke_failure_is_generic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = _TransactionEngine()
    revoke = Mock(side_effect=BootstrapServiceError())
    monkeypatch.setattr(bootstrap_cli, "revoke_bootstrap", revoke)
    monkeypatch.setattr(bootstrap_cli, "load_settings", lambda: _settings(None))
    monkeypatch.setattr(
        bootstrap_cli,
        "create_database_engine",
        lambda settings: engine,
    )

    assert bootstrap_cli.main(["revoke", str(FIXED_BOOTSTRAP_ID)]) == 1

    _assert_generic_failure(capsys, str(FIXED_BOOTSTRAP_ID))
    revoke.assert_called_once_with(engine.connection, FIXED_BOOTSTRAP_ID)
    assert engine.events == ["rollback"]
    assert engine.disposed


def test_installed_console_failure_redacts_environment_and_arguments() -> None:
    executable_name = "device-watch-bootstrap.exe" if os.name == "nt" else "device-watch-bootstrap"
    executable_path = Path(sys.executable).with_name(executable_name)
    environment: dict[str, str] = dict(os.environ)
    database_value = (
        "mysql+pymysql://subprocess-user:database-private-value@db:not-a-port/"
        "device_watch"
    )
    pepper_value = "subprocess-private-pepper-material-32-bytes-minimum"
    label_value = "subprocess-private-label"
    environment.update(
        {
            "DEVICE_WATCH_ENV": "test",
            "DATABASE_URL": database_value,
            "DEVICE_WATCH_BOOTSTRAP_HMAC_PEPPER": pepper_value,
        }
    )

    completed = subprocess.run(
        [str(executable_path), "create", "--label", label_value],
        cwd=Path(__file__).resolve().parents[3],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    combined_output = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert completed.stderr == "Bootstrap operation failed\n"
    for sensitive_value in (
        database_value,
        "subprocess-user",
        "database-private-value",
        pepper_value,
        label_value,
    ):
        assert sensitive_value not in combined_output

