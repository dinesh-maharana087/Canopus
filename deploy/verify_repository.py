"""Audit repository security and Stage 1 executable boundaries."""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Finding:
    """Sanitized audit finding with no source-value echo."""

    path: str
    rule: str
    message: str


_EXCLUDED_PARTS = {
    ".git",
    ".git.codex-generated",
    ".tmp",
    ".worktrees",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
_TEXT_SUFFIXES = {
    ".c",
    ".cfg",
    ".css",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}
_PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
_DATABASE_URL = re.compile(r"\b(?:postgres(?:ql)?|sqlite|mongodb|redis)://", re.IGNORECASE)
_LIVE_SECRET = re.compile(
    r"\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*([^\s$<{\[\]}'\"]+)",
    re.IGNORECASE,
)
_ROUTE = re.compile(r"(?:add_api_route|@?(?:app|router)\.(?:get|post|put|patch|delete))\s*\(\s*[\"']([^\"']+)")


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _excluded(path: Path) -> bool:
    return any(part in _EXCLUDED_PARTS for part in path.parts)


def _files(root: Path) -> Iterable[tuple[Path, str]]:
    for path in root.rglob("*"):
        if not path.is_file() or _excluded(path):
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES and path.name not in {".env", "Dockerfile", "Caddyfile"}:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def _is_example(path: Path) -> bool:
    return path.name == ".env.example" or path.name.endswith(".example")


def _is_production_surface(relative: str) -> bool:
    return relative.startswith(("server/src/", "agent/src/", "web/src/", "deploy/"))


def _finding(root: Path, path: Path, rule: str, message: str) -> Finding:
    return Finding(_relative(root, path), rule, message)


def audit_repository(root: Path) -> list[Finding]:
    """Return sanitized findings for security and Stage 1 boundary violations."""

    findings: list[Finding] = []
    contents = list(_files(root))

    for path, text in contents:
        relative = _relative(root, path)
        is_test = "/tests/" in f"/{relative}"
        if _PRIVATE_KEY.search(text):
            findings.append(_finding(root, path, "private-key", "private-key material is present"))

        if path.name == ".env" or (path.name.startswith(".env.") and not _is_example(path)):
            findings.append(_finding(root, path, "live-environment", "live environment files must not be committed"))

        if not is_test and not _is_example(path) and _LIVE_SECRET.search(text):
            findings.append(_finding(root, path, "live-credential", "credential-like literal found outside an example file"))

        if not is_test and _is_production_surface(relative) and _DATABASE_URL.search(text):
            findings.append(_finding(root, path, "database-allowlist", "unsupported database URL scheme"))

        if relative.startswith("server/src/"):
            for match in _ROUTE.finditer(text):
                if match.group(1) not in {"/api/v1/health/live", "/api/v1/health/ready"}:
                    findings.append(_finding(root, path, "business-route", "non-health API route is present"))
            if re.search(r"class\s+\w+\s*\(\s*Base\s*\)|__tablename__\s*=", text):
                findings.append(_finding(root, path, "domain-table", "mapped domain table is present"))

        if relative.startswith("agent/src/"):
            if path.name.lower() in {"sender.py", "transport.py"} or "sender" in path.stem.lower():
                findings.append(_finding(root, path, "sender", "production sender module is present"))
            if path.name != "contracts.py" and re.search(r"async\s+def\s+collect\s*\(", text):
                findings.append(_finding(root, path, "concrete-collector", "production collector implementation is present"))

        if relative.startswith("web/src/"):
            if re.search(r"\bfetch\s*\(|XMLHttpRequest|\.open\s*\(\s*[\"'](?:GET|POST|PUT|PATCH|DELETE)", text):
                findings.append(_finding(root, path, "frontend-api", "frontend network API call is present"))
            if re.search(r"(?:device_id|heartbeat|observed_at|monitoring_records?)\s*[:=]", text, re.IGNORECASE):
                findings.append(_finding(root, path, "monitoring-fixture", "monitoring data fixture is present"))

    production_compose = root / "deploy" / "compose.prod.yml"
    if production_compose.exists():
        text = production_compose.read_text(encoding="utf-8")
        service_block = re.search(r"^services:\s*\n(?P<body>.*?)(?=^networks:|^volumes:|^secrets:|\Z)", text, re.MULTILINE | re.DOTALL)
        if service_block:
            service_names = set(re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", service_block.group("body"), re.MULTILINE))
            if service_names != {"caddy", "server"}:
                findings.append(_finding(root, production_compose, "production-services", "production Compose must contain only caddy and server"))
        server_block = re.search(r"^  server:\s*\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\s*$|^networks:|\Z)", text, re.MULTILINE | re.DOTALL)
        if server_block and re.search(r"^\s+ports:\s*$", server_block.group("body"), re.MULTILINE):
            findings.append(_finding(root, production_compose, "server-port", "production server must not publish a host port"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the Device Watch Stage 1 repository")
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    findings = audit_repository(args.root.resolve())
    for finding in findings:
        print(f"{finding.path}: {finding.rule}: {finding.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
