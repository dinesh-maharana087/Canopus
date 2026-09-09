from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from device_watch_server.core.config import (
    Environment,
    Settings,
    SettingsError,
    load_settings,
)

VALID_DATABASE_URL = (
    "mysql+pymysql://device_watch:secret@db:3306/device_watch"
)
PRODUCTION_DATABASE_URL = (
    f"{VALID_DATABASE_URL}"
    "?ssl_ca=%2Frun%2Fsecrets%2Fmysql-ca.pem"
    "&ssl_verify_cert=true&ssl_verify_identity=true"
)


def set_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    database_url: str = VALID_DATABASE_URL,
) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", environment)
    monkeypatch.setenv("DATABASE_URL", database_url)


def test_documented_uppercase_names_load_from_case_sensitive_environment() -> None:
    case_sensitive_environment = {
        "DEVICE_WATCH_ENV": "test",
        "DATABASE_URL": VALID_DATABASE_URL,
    }

    with patch("os.environ", case_sensitive_environment):
        settings = load_settings()

    assert settings.device_watch_env is Environment.TEST
    assert settings.database_url.get_secret_value() == VALID_DATABASE_URL


def test_missing_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)

    with pytest.raises(SettingsError, match="DEVICE_WATCH_ENV"):
        load_settings()


def test_missing_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVICE_WATCH_ENV", "test")

    with pytest.raises(SettingsError, match="DATABASE_URL"):
        load_settings()


def test_non_mysql_pymysql_dialect_is_rejected() -> None:
    with pytest.raises(ValidationError, match="mysql\\+pymysql"):
        Settings(
            device_watch_env="test",
            database_url="postgresql://user:password@db/device_watch",
        )


def test_environment_accepts_only_three_named_modes() -> None:
    for value, database_url in (
        ("development", VALID_DATABASE_URL),
        ("test", VALID_DATABASE_URL),
        ("production", PRODUCTION_DATABASE_URL),
    ):
        settings = Settings(device_watch_env=value, database_url=database_url)
        assert settings.device_watch_env.value == value

    with pytest.raises(ValidationError):
        Settings(device_watch_env="staging", database_url=VALID_DATABASE_URL)


def test_settings_are_immutable_and_repr_does_not_expose_credentials() -> None:
    settings = Settings(device_watch_env=Environment.TEST, database_url=VALID_DATABASE_URL)

    assert "secret" not in repr(settings)
    with pytest.raises(ValidationError):
        settings.database_url = "mysql+pymysql://changed:password@db/device_watch"  # type: ignore[misc]


def test_invalid_url_error_does_not_expose_database_credentials() -> None:
    credentialed_url = "mysql+pymysql://private-user:private-password@db:3306/device_watch"

    with pytest.raises(ValidationError) as error:
        Settings(
            device_watch_env="test",
            database_url=credentialed_url.replace("db:3306", "db:not-a-port"),
        )

    assert "private-user" not in str(error.value)
    assert "private-password" not in str(error.value)


def test_production_requires_exact_ca_path_and_true_verification_flags() -> None:
    settings = Settings(device_watch_env="production", database_url=PRODUCTION_DATABASE_URL)
    assert settings.device_watch_env is Environment.PRODUCTION

    for query in (
        "ssl_verify_cert=true&ssl_verify_identity=true",
        "ssl_ca=/wrong.pem&ssl_verify_cert=true&ssl_verify_identity=true",
        "ssl_ca=/run/secrets/mysql-ca.pem&ssl_verify_cert=false&ssl_verify_identity=true",
    ):
        with pytest.raises(ValidationError, match="exact production TLS"):
            Settings(
                device_watch_env="production",
                database_url=f"{VALID_DATABASE_URL}?{query}",
            )


def test_production_rejects_duplicate_or_additional_query_keys() -> None:
    duplicate = (
        f"{VALID_DATABASE_URL}?ssl_ca=%2Frun%2Fsecrets%2Fmysql-ca.pem"
        "&ssl_ca=%2Frun%2Fsecrets%2Fmysql-ca.pem"
        "&ssl_verify_cert=true&ssl_verify_identity=true"
    )
    additional = f"{PRODUCTION_DATABASE_URL}&charset=utf8mb4"

    for database_url in (duplicate, additional):
        with pytest.raises(ValidationError, match="exact production TLS"):
            Settings(device_watch_env="production", database_url=database_url)


def test_production_rejects_enabled_api_documentation() -> None:
    with pytest.raises(ValidationError, match="DEVICE_WATCH_ENABLE_DOCS"):
        Settings(
            device_watch_env="production",
            database_url=PRODUCTION_DATABASE_URL,
            device_watch_enable_docs=True,
        )


def test_development_can_omit_tls_for_isolated_database() -> None:
    settings = Settings(device_watch_env="development", database_url=VALID_DATABASE_URL)

    assert settings.device_watch_env is Environment.DEVELOPMENT
    assert settings.device_watch_enable_docs is False
