from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from verify_repository import AuditScope, audit_repository, main


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def rules(root: Path, *, scope: AuditScope = AuditScope.STAGE_ONE) -> set[str]:
    return {finding.rule for finding in audit_repository(root, scope=scope)}


def test_clean_stage_one_shape_passes(tmp_path: Path) -> None:
    write(tmp_path, "server/src/app.py", 'app.add_api_route("/api/v1/health/live", live)\n')
    write(tmp_path, "agent/src/device_watch_agent/collectors/contracts.py", "class Collector(Protocol):\n    async def collect(self): ...\n")
    write(tmp_path, ".env.example", "DATABASE_URL=mysql+pymysql://sample:sample@db/device_watch\n")
    write(tmp_path, "deploy/compose.prod.yml", "services:\n  caddy:\n    image: device-watch-caddy:stage1\n  server:\n    image: device-watch-server:stage1\n")
    assert audit_repository(tmp_path) == []


def test_security_and_dependency_findings_are_sanitized(tmp_path: Path) -> None:
    write(tmp_path, "keys.txt", "-----BEGIN " + "PRIVATE KEY-----\nprivate-value\n")
    write(tmp_path, ".env", "PASSWORD=live-password\n")
    write(tmp_path, "server/src/config.py", "DATABASE_URL=postgres" + "ql://user:password@db/app\n")
    findings = audit_repository(tmp_path)
    assert {finding.rule for finding in findings} >= {"private-key", "live-environment", "database-allowlist"}
    assert all("private-value" not in finding.message for finding in findings)
    assert all("live-password" not in finding.message for finding in findings)


def test_quoted_credentials_and_private_key_variants_are_rejected(tmp_path: Path) -> None:
    write(tmp_path, "config/runtime.toml", 'password = "quoted-private-value"\n')
    write(tmp_path, "config/runtime.json", '{"password": "json-private-value"}\n')
    write(
        tmp_path,
        "config/encrypted.pem",
        "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----\nencrypted-private-value\n",
    )
    write(
        tmp_path,
        "config/dsa.key",
        "-----BEGIN " + "DSA PRIVATE KEY-----\ndsa-private-value\n",
    )
    write(tmp_path, "config/operator.p12", "opaque-private-key-bundle\n")

    findings = audit_repository(tmp_path)

    assert {
        (finding.path, finding.rule)
        for finding in findings
    } >= {
        ("config/runtime.toml", "live-credential"),
        ("config/runtime.json", "live-credential"),
        ("config/encrypted.pem", "private-key"),
        ("config/dsa.key", "private-key"),
        ("config/operator.p12", "private-key"),
    }
    assert all("quoted-private-value" not in finding.message for finding in findings)
    assert all("encrypted-private-value" not in finding.message for finding in findings)
    assert all("dsa-private-value" not in finding.message for finding in findings)
    assert all("json-private-value" not in finding.message for finding in findings)
    assert all("opaque-private-key-bundle" not in finding.message for finding in findings)


def test_database_allowlist_rejects_unknown_and_test_database_urls(
    tmp_path: Path,
) -> None:
    unknown_url = "newdb+driver:" + "//user:password@db/app"
    local_url = "sqlite+pysqlite:" + "///:memory:"
    write(
        tmp_path,
        "config/database.env",
        f'DATABASE_URL = "{unknown_url}"\n',
    )
    write(
        tmp_path,
        "server/tests/unit/test_local_database.py",
        f'engine = create_engine("{local_url}")\n',
    )
    write(
        tmp_path,
        "server/tests/unit/test_rejected_database_setting.py",
        f'Settings(database_url="{unknown_url}")\n',
    )
    write(
        tmp_path,
        "server/tests/unit/test_mysql_engine.py",
        'engine = create_engine("mysql+pymysql://sample:sample@db/device_watch")\n',
    )
    write(
        tmp_path,
        "server/src/allowed_database.py",
        'DATABASE_URL = "mysql+pymysql://sample:sample@db/device_watch"\n',
    )
    write(
        tmp_path,
        "config/not_a_database.env",
        'CALLBACK_URL = "https://service.example.test/callback"\n',
    )
    write(
        tmp_path,
        "config/wrong_database.env",
        'DATABASE_URL = "https://service.example.test/database"\n',
    )
    write(
        tmp_path,
        "server/src/async_database.py",
        'engine = create_async_engine("sqlite+aiosqlite:///:memory:")\n',
    )

    findings = audit_repository(tmp_path)
    database_paths = {
        finding.path
        for finding in findings
        if finding.rule == "database-allowlist"
    }

    assert database_paths == {
        "server/tests/unit/test_local_database.py",
        "config/database.env",
        "config/wrong_database.env",
        "server/src/async_database.py",
    }


def test_stage_two_source_boundaries_are_rejected(tmp_path: Path) -> None:
    write(tmp_path, "server/src/routes.py", '@app.get("/api/v1/devices")(handler)\n')
    write(tmp_path, "server/src/models.py", "class Device(Base):\n    __tablename__ = 'devices'\n")
    write(tmp_path, "agent/src/device_watch_agent/collectors/cpu.py", "class CpuCollector:\n    async def collect(self): ...\n")
    write(tmp_path, "agent/src/device_watch_agent/sender.py", "def send(): pass\n")
    write(tmp_path, "web/src/api.ts", "fetch('/api/v1/devices')\n")
    write(tmp_path, "web/src/data.ts", "const device_id = 'sample'\n")
    assert rules(tmp_path) >= {
        "business-route",
        "domain-table",
        "concrete-collector",
        "sender",
        "frontend-api",
        "monitoring-fixture",
    }


def test_stage_two_migrations_and_server_modules_are_rejected(tmp_path: Path) -> None:
    write(
        tmp_path,
        "server/alembic/versions/20260908_0002_devices.py",
        "def upgrade():\n    op.create_table('devices')\n",
    )
    write(
        tmp_path,
        "server/src/device_watch_server/enrollment/service.py",
        "def issue_credential(): pass\n",
    )

    findings = audit_repository(tmp_path)
    path_rules = {(finding.path, finding.rule) for finding in findings}

    assert path_rules >= {
        (
            "server/alembic/versions/20260908_0002_devices.py",
            "stage-one-migration",
        ),
        ("server/alembic/versions/20260908_0002_devices.py", "domain-table"),
        (
            "server/src/device_watch_server/enrollment/service.py",
            "stage-one-source",
        ),
    }


def test_current_scope_skips_only_historical_stage_one_boundaries(
    tmp_path: Path,
) -> None:
    write(
        tmp_path,
        "server/alembic/versions/20260908_0002_devices.py",
        "def upgrade():\n    op.create_table('devices')\n",
    )
    write(
        tmp_path,
        "server/src/device_watch_server/enrollment/service.py",
        "def issue_credential(): pass\n",
    )
    write(tmp_path, "config/runtime.toml", 'password = "quoted-private-value"\n')
    write(tmp_path, "config/operator.p12", "opaque-private-key-bundle\n")
    write(tmp_path, "config/database.env", 'DATABASE_URL = "otherdb://db/app"\n')

    stage_one_rules = rules(tmp_path, scope=AuditScope.STAGE_ONE)
    current_rules = rules(tmp_path, scope=AuditScope.CURRENT)

    assert stage_one_rules >= {
        "domain-table",
        "database-allowlist",
        "live-credential",
        "private-key",
        "stage-one-migration",
        "stage-one-source",
    }
    assert current_rules == {
        "database-allowlist",
        "live-credential",
        "private-key",
    }


def test_cli_scope_distinguishes_current_from_stage_one(tmp_path: Path) -> None:
    write(
        tmp_path,
        "server/src/device_watch_server/enrollment/service.py",
        "def issue_credential(): pass\n",
    )

    assert main([str(tmp_path), "--scope", "current"]) == 0
    assert main([str(tmp_path), "--scope", "stage-one"]) == 1


def test_forbidden_production_topology_is_rejected(tmp_path: Path) -> None:
    write(
        tmp_path,
        "deploy/compose.prod.yml",
        """services:
  caddy:
    image: caddy:latest
  server:
    image: server:latest
    ports:
      - \"8000:8000\"
  mysql:
    image: mysql:8.4.11
networks:
  default: {}
""",
    )
    assert rules(tmp_path) >= {"production-services", "server-port"}
