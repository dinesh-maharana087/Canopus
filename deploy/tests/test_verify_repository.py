from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from verify_repository import audit_repository


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def rules(root: Path) -> set[str]:
    return {finding.rule for finding in audit_repository(root)}


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
