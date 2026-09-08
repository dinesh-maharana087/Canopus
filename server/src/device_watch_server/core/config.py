"""Validated environment configuration for the Device Watch server."""

from __future__ import annotations

from enum import Enum
from urllib.parse import parse_qsl, urlsplit

from pydantic import SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Environment(str, Enum):
    """Runtime environments supported by the server."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class SettingsError(ValueError):
    """Raised when required server configuration is missing or unsafe."""


PRODUCTION_TLS_QUERY = {
    "ssl_ca": "/run/secrets/mysql-ca.pem",
    "ssl_verify_cert": "true",
    "ssl_verify_identity": "true",
}


class Settings(BaseSettings):
    """Immutable server settings loaded from explicitly named environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_prefix="",
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )

    device_watch_env: Environment
    database_url: SecretStr
    device_watch_enable_docs: bool = False
    device_watch_bootstrap_hmac_pepper: SecretStr | None = None

    @field_validator("device_watch_bootstrap_hmac_pepper")
    @classmethod
    def validate_bootstrap_hmac_pepper(
        cls, value: SecretStr | None
    ) -> SecretStr | None:
        """Require enough UTF-8 entropy material whenever a pepper is configured."""

        if value is not None and len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError(
                "DEVICE_WATCH_BOOTSTRAP_HMAC_PEPPER must contain at least 32 UTF-8 bytes"
            )
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        """Require the one supported SQLAlchemy dialect without exposing the URL."""

        try:
            url = make_url(value.get_secret_value())
        except Exception as exc:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from exc

        if url.drivername != "mysql+pymysql":
            raise ValueError("DATABASE_URL must use the mysql+pymysql dialect")
        return value

    @model_validator(mode="after")
    def validate_environment_policy(self) -> Settings:
        """Apply environment-specific policy before any engine can be created."""

        if self.device_watch_env is Environment.PRODUCTION:
            if self.device_watch_enable_docs:
                raise ValueError("DEVICE_WATCH_ENABLE_DOCS cannot be enabled in production")
            self._validate_production_tls()
        return self

    def _validate_production_tls(self) -> None:
        """Require exactly the verified TLS query entries in production URLs."""

        raw_url = self.database_url.get_secret_value()
        query = urlsplit(raw_url).query
        pairs = parse_qsl(query, keep_blank_values=True)
        if len(pairs) != len(PRODUCTION_TLS_QUERY):
            raise ValueError("DATABASE_URL must contain the exact production TLS parameters")

        if dict(pairs) != PRODUCTION_TLS_QUERY or {
            key for key, _ in pairs
        } != set(PRODUCTION_TLS_QUERY):
            raise ValueError("DATABASE_URL must contain the exact production TLS parameters")


def load_settings() -> Settings:
    """Load settings and convert validation failures into secret-safe errors."""

    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        names = {
            str(error["loc"][0]).upper()
            for error in exc.errors(include_input=False)
            if error.get("loc")
        }
        fields = ", ".join(sorted(names)) or "server configuration"
        raise SettingsError(f"Invalid required configuration: {fields}") from None
    except ValueError as exc:
        message = str(exc)
        if "DATABASE_URL" in message:
            raise SettingsError(message) from None
        raise SettingsError(message) from None


def database_url(settings: Settings) -> URL:
    """Return the validated SQLAlchemy URL without exposing its secret value."""

    return make_url(settings.database_url.get_secret_value())


__all__ = [
    "PRODUCTION_TLS_QUERY",
    "Environment",
    "Settings",
    "SettingsError",
    "database_url",
    "load_settings",
]
