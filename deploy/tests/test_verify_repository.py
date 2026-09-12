from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

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


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit_fixture(root: Path) -> str:
    git(root, "add", ".")
    git(
        root, "-c", "user.name=Audit fixture", "-c", "user.email=audit@example.test",
        "-c", "commit.gpgsign=false", "commit", "-qm", "Audit fixture",
    )
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def stage_one_history(tmp_path: Path) -> tuple[Path, str]:
    git(tmp_path, "init", "-q")
    write(
        tmp_path, "server/src/device_watch_server/app.py",
        'app.add_api_route("/api/v1/health/live", live)\n',
    )
    write(
        tmp_path, "server/alembic/versions/20260831_0001_baseline.py",
        "def upgrade(): pass\n",
    )
    return tmp_path, commit_fixture(tmp_path)


def test_historical_stage_one_commit_passes_with_explicit_provenance(
    stage_one_history: tuple[Path, str], capsys: pytest.CaptureFixture[str],
) -> None:
    root, revision = stage_one_history

    assert main([str(root), "--stage-one-ref", revision]) == 0
    assert capsys.readouterr().out == f"Stage 1 snapshot: {revision}\n"


def test_later_additions_and_dirty_stage_one_files_do_not_rewrite_history(
    stage_one_history: tuple[Path, str], capsys: pytest.CaptureFixture[str],
) -> None:
    root, revision = stage_one_history
    write(
        root, "server/src/device_watch_server/enrollment/service.py",
        "def provision_bootstrap(): pass\n",
    )
    write(
        root, "server/alembic/versions/20260908_0002_devices.py",
        "def upgrade():\n    op.create_table('devices')\n",
    )
    commit_fixture(root)
    # A changed foundation needs its own re-verification, not a rewritten past.
    write(
        root, "server/src/device_watch_server/app.py",
        'app.add_api_route("/api/v1/enroll", enroll)\n',
    )
    before = git(root, "status", "--porcelain")

    assert main([str(root), "--stage-one-ref", revision]) == 0
    assert capsys.readouterr().out == f"Stage 1 snapshot: {revision}\n"
    assert audit_repository(root, scope=AuditScope.CURRENT) == []
    assert rules(root) >= {"stage-one-source", "stage-one-migration", "business-route"}
    assert git(root, "status", "--porcelain") == before


@pytest.mark.parametrize(
    "source",
    (
        "import device_watch_server.enrollment.service as bootstrap\n",
        "from device_watch_server.enrollment import service\n",
        "from device_watch_server import enrollment\n",
        "from . import enrollment\n",
        "from .domain.contracts import BootstrapState\n",
    ),
)
def test_stage_one_source_cannot_depend_on_later_modules(
    tmp_path: Path, source: str,
) -> None:
    write(tmp_path, "server/src/device_watch_server/app.py", source)

    assert "stage-one-import" in rules(tmp_path)
    assert audit_repository(tmp_path, scope=AuditScope.CURRENT) == []


def test_stage_one_module_and_exported_symbol_imports_remain_valid(
    tmp_path: Path,
) -> None:
    write(
        tmp_path, "server/src/device_watch_server/api/__init__.py",
        "from .router import api_router\n",
    )
    write(
        tmp_path, "server/src/device_watch_server/app.py",
        "from .api import router, api_router\n"
        "from device_watch_server.core.config import Settings\n",
    )

    assert audit_repository(tmp_path) == []


@pytest.mark.parametrize(
    "source",
    (
        'app.add_api_route("/api/v1/enroll", enroll)\n',
        'from fastapi import APIRouter as Router\n'
        'enrollment = Router()\n'
        '@enrollment.post("/api/v1/enroll")\ndef enroll(): pass\n',
        'from fastapi import APIRouter\n'
        'router = APIRouter(prefix="/api/v1/enroll")\n',
        'app.include_router(health_router, prefix="/api/v1/enroll")\n',
        'from device_watch_server.api.health import router as health_routes\n'
        '@health_routes.post("/api/v1/enroll")\ndef enroll(): pass\n',
        'routes = router\n@routes.post("/api/v1/enroll")\ndef enroll(): pass\n',
        'routes = router\nroutes.include_router(health_router, prefix="/api/v1/enroll")\n',
        'from fastapi import APIRouter\nrouter = APIRouter(prefix=f"{stage2_prefix}")\n',
        '@router.get(f"/api/v1/health/live{suffix}")\ndef enroll(): pass\n',
    ),
)
def test_stage_one_source_cannot_expose_later_workflow(
    tmp_path: Path, source: str,
) -> None:
    write(tmp_path, "server/src/device_watch_server/app.py", source)

    assert "business-route" in rules(tmp_path)
    assert audit_repository(tmp_path, scope=AuditScope.CURRENT) == []


def test_leakage_in_historical_commit_is_not_hidden_by_clean_current_files(
    stage_one_history: tuple[Path, str], capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = stage_one_history
    write(
        root, "server/src/device_watch_server/app.py",
        "from .enrollment import service\n",
    )
    leaked_revision = commit_fixture(root)
    write(root, "server/src/device_watch_server/app.py", "# clean working file\n")

    assert main([str(root), "--stage-one-ref", leaked_revision]) == 1
    output = capsys.readouterr().out
    assert f"Stage 1 snapshot: {leaked_revision}" in output
    assert "stage-one-import" in output


def test_archive_export_attributes_cannot_hide_historical_leakage(
    stage_one_history: tuple[Path, str], capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = stage_one_history
    write(root, ".gitattributes", "server/src/device_watch_server/app.py export-ignore\n")
    write(
        root, "server/src/device_watch_server/app.py",
        "from .enrollment import service\n",
    )
    revision = commit_fixture(root)

    assert main([str(root), "--stage-one-ref", revision]) == 1
    assert "stage-one-import" in capsys.readouterr().out


def test_git_replacements_cannot_hide_historical_leakage(
    stage_one_history: tuple[Path, str], capsys: pytest.CaptureFixture[str],
) -> None:
    root, clean_revision = stage_one_history
    write(
        root, "server/src/device_watch_server/app.py",
        "from .enrollment import service\n",
    )
    leaked_revision = commit_fixture(root)
    git(root, "replace", leaked_revision, clean_revision)

    assert main([str(root), "--stage-one-ref", leaked_revision]) == 1
    assert "stage-one-import" in capsys.readouterr().out


@pytest.mark.parametrize("revision", ("absent-private-value", "HEAD:server/src/device_watch_server/app.py"))
def test_invalid_or_non_commit_snapshot_fails_without_current_tree_fallback(
    stage_one_history: tuple[Path, str], revision: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = stage_one_history

    assert main([str(root), "--stage-one-ref", revision]) == 2
    output = capsys.readouterr().out
    assert output == "historical-snapshot: unable to audit the requested Stage 1 commit\n"
    assert revision not in output


def test_snapshot_requires_a_repository(tmp_path: Path) -> None:
    assert main([str(tmp_path), "--stage-one-ref", "HEAD"]) == 2


def test_current_scope_cannot_be_replaced_by_a_historical_snapshot(
    stage_one_history: tuple[Path, str],
) -> None:
    root, revision = stage_one_history
    with pytest.raises(SystemExit) as error:
        main([str(root), "--scope", "current", "--stage-one-ref", revision])
    assert error.value.code == 2
