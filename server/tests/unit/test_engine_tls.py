from __future__ import annotations

import importlib.metadata

import pytest
from sqlalchemy import event
from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql
from sqlalchemy.engine import make_url

from device_watch_server.core.config import Environment, Settings
from device_watch_server.db.engine import (
    create_database_engine,
    database_engine_url,
    validated_connect_args,
)

VALID_DATABASE_URL = (
    "mysql+pymysql://device_watch:secret@db:3306/device_watch"
)
PRODUCTION_DATABASE_URL = (
    f"{VALID_DATABASE_URL}"
    "?ssl_ca=%2Frun%2Fsecrets%2Fmysql-ca.pem"
    "&ssl_verify_cert=true&ssl_verify_identity=true"
)


def test_engine_configures_pre_ping_and_recycling_without_connecting() -> None:
    settings = Settings(
        device_watch_env=Environment.TEST,
        database_url=VALID_DATABASE_URL,
    )
    engine = create_database_engine(settings)

    try:
        assert engine.pool._pre_ping is True
        assert engine.pool._recycle == 1_800
    finally:
        engine.dispose()


def test_locked_sqlalchemy_pymysql_url_translation_characterization() -> None:
    url = make_url(
        "mysql+pymysql://user:secret@db:3306/device_watch"
        "?ssl_ca=%2Frun%2Fsecrets%2Fmysql-ca.pem"
        "&ssl_verify_cert=true&ssl_verify_identity=true"
    )
    dialect = MySQLDialect_pymysql()
    _, translated = dialect.create_connect_args(url)

    assert importlib.metadata.version("SQLAlchemy") == "2.0.52"
    assert importlib.metadata.version("PyMySQL") == "1.2.0"
    assert translated["ssl"] == {"ca": "/run/secrets/mysql-ca.pem"}
    assert translated["ssl_verify_cert"] == "true"
    assert translated["ssl_verify_identity"] == "true"


def test_production_connect_args_use_boolean_certificate_and_identity_checks() -> None:
    settings = Settings(
        device_watch_env=Environment.PRODUCTION,
        database_url=PRODUCTION_DATABASE_URL,
    )

    assert validated_connect_args(settings) == {
        "ssl_ca": "/run/secrets/mysql-ca.pem",
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    }


def test_engine_passes_validated_tls_values_to_pymysql() -> None:
    class ConnectionIntercepted(RuntimeError):
        pass

    settings = Settings(
        device_watch_env=Environment.PRODUCTION,
        database_url=PRODUCTION_DATABASE_URL,
    )
    captured: dict[str, object] = {}
    engine = create_database_engine(settings)

    @event.listens_for(engine, "do_connect")
    def capture_effective_parameters(
        dialect: object,
        connection_record: object,
        positional: list[object],
        keyword: dict[str, object],
    ) -> None:
        del dialect, connection_record, positional
        captured.update(keyword)
        raise ConnectionIntercepted

    with pytest.raises(ConnectionIntercepted):
        engine.connect()

    assert captured["ssl_ca"] == "/run/secrets/mysql-ca.pem"
    assert captured["ssl_verify_cert"] is True
    assert captured["ssl_verify_identity"] is True
    assert "ssl" not in captured
    engine.dispose()


def test_database_engine_url_removes_tls_query_before_sqlalchemy_translation() -> None:
    settings = Settings(
        device_watch_env=Environment.PRODUCTION,
        database_url=PRODUCTION_DATABASE_URL,
    )

    url = database_engine_url(settings)
    assert url.query.get("ssl_ca") is None
    assert url.query.get("ssl_verify_cert") is None
    assert url.query.get("ssl_verify_identity") is None
    assert url.drivername == "mysql+pymysql"
    assert url.host == "db"
    assert url.database == "device_watch"
